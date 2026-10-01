from enum import Enum
class CognitiveErrorCode(str,Enum):
    INVALID_REQUEST="INVALID_REQUEST"; MISSING_ENTITY="MISSING_ENTITY"; RETRIEVAL_FAILED="RETRIEVAL_FAILED"; INVALID_CONFIG="INVALID_CONFIG"
class CognitiveError(Exception):
    def __init__(self,code,message): self.code=code; super().__init__(message)
