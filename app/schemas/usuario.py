from pydantic import BaseModel, ConfigDict

from app.models.usuario import RoleEnum


class UsuarioPublic(BaseModel):
    id: str
    nome: str
    email: str
    role: RoleEnum

    #              Essa parte é responsável por fazer a conversão automática ex: joao.nome, joao.email
    #              do objeto inserido invés de passar {"nome": "João",
    #   "email": "..."}.       
    model_config = ConfigDict(from_attributes=True)
