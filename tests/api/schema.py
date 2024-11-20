from typing import List, Optional

from pydantic import RootModel, BaseModel, Field


class PetBase(BaseModel):
    name: str
    tag: Optional[str] = None


class PetCreate(PetBase):
    pass


class Pet(PetBase):
    id: int


class Pets(RootModel):
    root: List[Pet] = Field(..., description='list of pet')


class Error(BaseModel):
    code: int
    message: str
