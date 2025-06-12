from typing import List, Optional

from pydantic import BaseModel


class ContentItem(BaseModel):
    type: str
    text: str


class Result(BaseModel):
    content: List[ContentItem]


class JSONRPCErrorModel(BaseModel):
    code: int
    message: str


class ErrorContentItem(BaseModel):
    type: str
    text: str


class JSONRPCResponse(BaseModel):
    jsonrpc: str
    id: Optional[str]
    result: Optional[Result] = None
    error: Optional[JSONRPCErrorModel] = None
    errorContent: Optional[List[ErrorContentItem]] = None
