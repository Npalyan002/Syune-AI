from typing import Protocol
from dataclasses import dataclass
from .model import Locator,MediaMetadata,RepresentationType
@dataclass(frozen=True,slots=True)
class ProviderOutput:
    content:str;locator:Locator;representation:RepresentationType;confidence:float|None=None
class ImageUnderstandingProvider(Protocol):
    provider_id:str;model_id:str;model_version:str|None;execution_location:object
    def perceive(self,data:bytes,metadata:MediaMetadata)->tuple[ProviderOutput,...]:...
class SpeechToTextProvider(Protocol):
    provider_id:str;model_id:str;model_version:str|None;execution_location:object
    def perceive(self,data:bytes,metadata:MediaMetadata)->tuple[ProviderOutput,...]:...
class VideoUnderstandingProvider(Protocol):
    provider_id:str;model_id:str;model_version:str|None;execution_location:object
    def perceive(self,data:bytes,metadata:MediaMetadata)->tuple[ProviderOutput,...]:...
