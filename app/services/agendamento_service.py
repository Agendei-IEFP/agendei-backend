from datetime import datetime, date, timedelta, timezone, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.agendamento import Agendamento, StatusEnum
from app.models.horario_trabalho import HorarioTrabalho
from app.models.usuario import Usuario
from app.schemas.agendamento import AgendamentoCreate, AgendamentoUpdate, SlotDisponivel
from app.services.profissional_service import buscar_profissional
from app.services.servico_service import buscar_servico


# ---------------------------------------------------------------------------
# Algoritmo de slots disponíveis
# ---------------------------------------------------------------------------

async def listar_slots_disponiveis(
    db: AsyncSession,
    profissional_id: str,
    servico_id: str,
    data_consulta: date,
) -> list[SlotDisponivel]:
    """
    Retorna todos os horários livres para um profissional num dado dia.

    O algoritmo funciona assim:
    1. Busca o horário de trabalho do profissional naquele dia da semana.
       Se não trabalhar nesse dia, retorna lista vazia.
    2. Busca todos os agendamentos do dia que ainda "ocupam" o slot
       (status pendente ou confirmado).
    3. A partir do horário de início do expediente, gera slots de
       tamanho = duração do serviço, pulando os que colidem com
       agendamentos existentes.

    Por que armazenamos data_hora_fim no agendamento?
    Porque a query de colisão é simples e rápida:
        novo_inicio < existente_fim AND novo_fim > existente_inicio
    Se não armazenássemos, precisaríamos de um JOIN com serviços em
    cada verificação, o que seria custoso com muitos agendamentos.
    """
    await buscar_profissional(db, profissional_id)
    servico = await buscar_servico(db, servico_id)

    # Passo 1: existe horário de trabalho neste dia da semana?
    dia_semana = data_consulta.weekday()  # 0=segunda, 6=domingo
    result_horario = await db.execute(
        select(HorarioTrabalho).where(
            HorarioTrabalho.profissional_id == profissional_id,
            HorarioTrabalho.dia_semana == dia_semana,
            HorarioTrabalho.is_active.is_(True),
        )
    )
    horario = result_horario.scalar_one_or_none()
    if horario is None:
        return []  # profissional não trabalha neste dia

    # Passo 2: agendamentos que bloqueiam slots neste dia
    inicio_do_dia = datetime.combine(data_consulta, time.min).replace(tzinfo=timezone.utc)
    fim_do_dia = datetime.combine(data_consulta, time.max).replace(tzinfo=timezone.utc)

    result_agendamentos = await db.execute(
        select(Agendamento).where(
            Agendamento.profissional_id == profissional_id,
            Agendamento.data_hora_inicio >= inicio_do_dia,
            Agendamento.data_hora_inicio <= fim_do_dia,
            Agendamento.status.in_([StatusEnum.pendente, StatusEnum.confirmado]),
        )
    )
    agendamentos_ocupados = list(result_agendamentos.scalars().all())

    # Passo 3: gera slots e filtra os que colidem
    duracao = timedelta(minutes=servico.duracao_minutos)
    slots: list[SlotDisponivel] = []

    cursor = datetime.combine(data_consulta, horario.hora_inicio).replace(tzinfo=timezone.utc)
    fim_expediente = datetime.combine(data_consulta, horario.hora_fim).replace(tzinfo=timezone.utc)
    agora = datetime.now(timezone.utc)

    while cursor + duracao <= fim_expediente:
        slot_inicio = cursor
        slot_fim = cursor + duracao

        # Não retornar slots no passado
        if slot_inicio > agora:
            colide = _slot_colide(slot_inicio, slot_fim, agendamentos_ocupados)
            if not colide:
                slots.append(SlotDisponivel(inicio=slot_inicio, fim=slot_fim))

        cursor = cursor + duracao  # avança pelo tamanho do serviço

    return slots


def _slot_colide(
    inicio: datetime,
    fim: datetime,
    agendamentos: list[Agendamento],
) -> bool:
    """
    Verifica se um slot proposto colide com qualquer agendamento existente.

    A lógica de colisão de intervalos:
        dois intervalos [A, B] e [C, D] se sobrepõem se:
        A < D  AND  B > C

    O inverso (não colidem) seria:
        A >= D  OR  B <= C
    """
    for ag in agendamentos:
        if inicio < ag.data_hora_fim and fim > ag.data_hora_inicio:
            return True
    return False


# ---------------------------------------------------------------------------
# CRUD de agendamentos
# ---------------------------------------------------------------------------

async def criar_agendamento(
    db: AsyncSession,
    data: AgendamentoCreate,
    cliente: Usuario,
) -> Agendamento:
    """
    Cria um agendamento para o cliente autenticado.
    Valida:
      - O slot solicitado ainda está disponível (verificação final antes de gravar)
      - O serviço pertence ao profissional indicado
    """
    servico = await buscar_servico(db, data.servico_id)

    # Garante que o serviço pertence ao profissional correto
    if servico.profissional_id != data.profissional_id:
        raise HTTPException(
            status_code=422,
            detail="Este serviço não pertence ao profissional indicado",
        )

    data_hora_inicio = data.data_hora_inicio
    if data_hora_inicio.tzinfo is None:
        data_hora_inicio = data_hora_inicio.replace(tzinfo=timezone.utc)

    data_hora_fim = data_hora_inicio + timedelta(minutes=servico.duracao_minutos)

    # Verificação final de conflito — mesmo que o cliente tenha usado /slots,
    # pode ter havido uma corrida entre o GET e o POST.
    conflito = await db.execute(
        select(Agendamento).where(
            Agendamento.profissional_id == data.profissional_id,
            Agendamento.status.in_([StatusEnum.pendente, StatusEnum.confirmado]),
            Agendamento.data_hora_inicio < data_hora_fim,
            Agendamento.data_hora_fim > data_hora_inicio,
        )
    )
    if conflito.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Este horário não está mais disponível",
        )

    agendamento = Agendamento(
        cliente_id=cliente.id,
        profissional_id=data.profissional_id,
        servico_id=data.servico_id,
        data_hora_inicio=data_hora_inicio,
        data_hora_fim=data_hora_fim,
        status=StatusEnum.pendente,
    )
    db.add(agendamento)
    await db.commit()
    await db.refresh(agendamento)
    return agendamento


async def listar_agendamentos_do_cliente(
    db: AsyncSession, cliente: Usuario
) -> list[Agendamento]:
    result = await db.execute(
        select(Agendamento).where(
            Agendamento.cliente_id == cliente.id,
            Agendamento.deleted_at.is_(None),
        ).order_by(Agendamento.data_hora_inicio.desc())
    )
    return list(result.scalars().all())


async def listar_agendamentos_do_profissional(
    db: AsyncSession,
    profissional_id: str,
    usuario: Usuario,
) -> list[Agendamento]:
    """
    Profissional pode ver os próprios agendamentos.
    Admin da loja também pode, para gerir a agenda.
    """
    profissional = await buscar_profissional(db, profissional_id)

    # Profissional vendo a própria agenda
    eh_o_proprio = profissional.usuario_id == usuario.id

    # Admin da loja vendo a agenda de um profissional da sua loja
    from app.services.loja_service import get_loja
    loja = await get_loja(db, profissional.loja_id)
    eh_admin_da_loja = loja.owner_id == usuario.id

    if not eh_o_proprio and not eh_admin_da_loja:
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(Agendamento).where(
            Agendamento.profissional_id == profissional_id,
            Agendamento.deleted_at.is_(None),
        ).order_by(Agendamento.data_hora_inicio.desc())
    )
    return list(result.scalars().all())


async def buscar_agendamento(db: AsyncSession, agendamento_id: str) -> Agendamento:
    result = await db.execute(
        select(Agendamento).where(
            Agendamento.id == agendamento_id,
            Agendamento.deleted_at.is_(None),
        )
    )
    ag = result.scalar_one_or_none()
    if ag is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return ag


async def atualizar_status(
    db: AsyncSession,
    agendamento_id: str,
    data: AgendamentoUpdate,
    usuario: Usuario,
) -> Agendamento:
    """
    Transições de status permitidas:
      - pendente → confirmado  (profissional ou admin)
      - pendente → cancelado   (cliente, profissional ou admin)
      - confirmado → concluido (profissional ou admin)
      - confirmado → cancelado (cliente, profissional ou admin)

    Grava quem cancelou para auditoria.
    """
    ag = await buscar_agendamento(db, agendamento_id)

    # Verifica se o usuário tem permissão sobre este agendamento
    from app.services.profissional_service import buscar_profissional as bp
    profissional = await bp(db, ag.profissional_id)
    from app.services.loja_service import get_loja
    loja = await get_loja(db, profissional.loja_id)

    eh_cliente = ag.cliente_id == usuario.id
    eh_profissional = profissional.usuario_id == usuario.id
    eh_admin = loja.owner_id == usuario.id

    if not (eh_cliente or eh_profissional or eh_admin):
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Validação das transições
    TRANSICOES_VALIDAS = {
        StatusEnum.pendente: [StatusEnum.confirmado, StatusEnum.cancelado],
        StatusEnum.confirmado: [StatusEnum.concluido, StatusEnum.cancelado],
        StatusEnum.concluido: [],
        StatusEnum.cancelado: [],
    }
    if data.status not in TRANSICOES_VALIDAS[ag.status]:
        raise HTTPException(
            status_code=422,
            detail=f"Não é possível mover de '{ag.status}' para '{data.status}'",
        )

    # Clientes só podem cancelar, não confirmar nem concluir
    if eh_cliente and not (eh_profissional or eh_admin):
        if data.status != StatusEnum.cancelado:
            raise HTTPException(
                status_code=403,
                detail="Clientes só podem cancelar agendamentos",
            )

    ag.status = data.status
    if data.status == StatusEnum.cancelado:
        ag.cancelado_por = usuario.id
        ag.cancelado_motivo = data.motivo

    await db.commit()
    await db.refresh(ag)
    return ag