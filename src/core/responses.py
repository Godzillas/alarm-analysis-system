"""
统一响应模型
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(True, description="操作是否成功")
    message: str = Field("", description="响应消息")
    code: str = Field("SUCCESS", description="响应代码")


class DataResponse(BaseResponse, Generic[T]):
    """带数据的响应模型"""
    data: Optional[T] = Field(None, description="响应数据")


class ListResponse(BaseResponse, Generic[T]):
    """列表响应模型"""
    data: List[T] = Field(default_factory=list, description="列表数据")
    total: int = Field(0, description="总数量")


class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    data: List[T] = Field(default_factory=list, description="分页数据")
    total: int = Field(0, description="总数量")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    pages: int = Field(0, description="总页数")
    
    @classmethod
    def create(cls, data: List[T], total: int, page: int, page_size: int, message: str = "") -> "PaginatedResponse[T]":
        """创建分页响应"""
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            message=message
        )


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="操作是否成功")
    message: str = Field(..., description="错误消息")
    code: str = Field(..., description="错误代码")
    details: Dict[str, Any] = Field(default_factory=dict, description="错误详情")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本信息")
    timestamp: str = Field(..., description="检查时间")
    services: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="服务状态详情")


# 便捷函数
def success_response(message: str = "操作成功", code: str = "SUCCESS") -> BaseResponse:
    """创建成功响应"""
    return BaseResponse(success=True, message=message, code=code)


def data_response(data: T, message: str = "获取成功", code: str = "SUCCESS") -> DataResponse[T]:
    """创建数据响应"""
    return DataResponse(success=True, message=message, code=code, data=data)


def list_response(data: List[T], total: Optional[int] = None, message: str = "获取成功") -> ListResponse[T]:
    """创建列表响应"""
    if total is None:
        total = len(data)
    return ListResponse(success=True, message=message, data=data, total=total)


def error_response(message: str, code: str = "ERROR", details: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(
        message=message,
        code=code,
        details=details or {}
    )