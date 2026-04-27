from pydantic import BaseModel, Field


class ComponentSpec(BaseModel):
    type: str
    props: dict = Field(default_factory=dict)


class ScreenSpec(BaseModel):
    id: str
    name: str
    components: list[ComponentSpec] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)


class MetaSpec(BaseModel):
    project: str
    version: str = "v1"


class UISpec(BaseModel):
    meta: MetaSpec
    screens: list[ScreenSpec]
