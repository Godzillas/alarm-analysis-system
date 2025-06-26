"""
告警去重管理API
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.services.deduplication_engine import (
    deduplication_engine, 
    DeduplicationConfig, 
    FingerprintStrategy
)
from src.api.auth import get_current_admin_user

router = APIRouter()


class DeduplicationConfigRequest(BaseModel):
    """去重配置请求模型"""
    strategy: str = "normal"
    time_window_minutes: int = 60
    similarity_threshold: float = 0.85
    enabled: bool = True


class DeduplicationStatsResponse(BaseModel):
    """去重统计响应模型"""
    total_alarms: int
    duplicate_alarms: int
    unique_alarms: int
    deduplication_rate: float
    time_window: str
    config: Dict[str, Any]


@router.get("/stats", response_model=DeduplicationStatsResponse)
async def get_deduplication_stats():
    """获取去重统计信息"""
    try:
        stats = await deduplication_engine.get_deduplication_stats()
        return DeduplicationStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取去重统计失败: {str(e)}")


@router.get("/config")
async def get_deduplication_config():
    """获取当前去重配置"""
    try:
        config = deduplication_engine.config
        return {
            "strategy": config.strategy.value,
            "time_window_minutes": config.time_window_minutes,
            "similarity_threshold": config.similarity_threshold,
            "enabled": config.enabled,
            "custom_fields": config.custom_fields,
            "exclude_fields": config.exclude_fields
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config")
async def update_deduplication_config(
    config_request: DeduplicationConfigRequest,
    current_user=Depends(get_current_admin_user)
):
    """更新去重配置（需要管理员权限）"""
    try:
        # 验证策略
        try:
            strategy = FingerprintStrategy(config_request.strategy)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的指纹策略: {config_request.strategy}"
            )
        
        # 验证参数
        if not 0.1 <= config_request.similarity_threshold <= 1.0:
            raise HTTPException(
                status_code=400,
                detail="相似度阈值必须在0.1-1.0之间"
            )
        
        if config_request.time_window_minutes < 1:
            raise HTTPException(
                status_code=400,
                detail="时间窗口必须大于0分钟"
            )
        
        # 创建新配置
        new_config = DeduplicationConfig(
            strategy=strategy,
            time_window_minutes=config_request.time_window_minutes,
            similarity_threshold=config_request.similarity_threshold,
            enabled=config_request.enabled
        )
        
        # 更新配置
        await deduplication_engine.update_config(new_config)
        
        return {"message": "去重配置更新成功", "config": config_request.dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/test-fingerprint")
async def test_fingerprint_generation(
    alarm_data: Dict[str, Any],
    strategy: str = "normal"
):
    """测试指纹生成（用于调试）"""
    try:
        from src.services.deduplication_engine import AlarmFingerprint
        
        # 验证策略
        try:
            fingerprint_strategy = FingerprintStrategy(strategy)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的指纹策略: {strategy}"
            )
        
        generator = AlarmFingerprint(fingerprint_strategy)
        fingerprint = generator.generate_fingerprint(alarm_data)
        
        return {
            "fingerprint": fingerprint,
            "strategy": strategy,
            "alarm_data": alarm_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"指纹生成测试失败: {str(e)}")


@router.post("/test-similarity")
async def test_similarity_calculation(
    alarm1: Dict[str, Any],
    alarm2: Dict[str, Any]
):
    """测试相似度计算（用于调试）"""
    try:
        from src.services.deduplication_engine import SimilarityCalculator
        
        calculator = SimilarityCalculator()
        similarity = calculator.calculate_similarity(alarm1, alarm2)
        
        return {
            "similarity": similarity,
            "alarm1": alarm1,
            "alarm2": alarm2,
            "is_similar": similarity >= deduplication_engine.config.similarity_threshold
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"相似度计算测试失败: {str(e)}")


@router.get("/strategies")
async def get_available_strategies():
    """获取可用的指纹策略"""
    return {
        "strategies": [
            {
                "value": strategy.value,
                "name": strategy.value.title(),
                "description": {
                    "strict": "严格模式：所有关键字段完全匹配",
                    "normal": "普通模式：核心字段匹配 + 模糊匹配", 
                    "loose": "宽松模式：主要字段匹配，忽略细节差异"
                }.get(strategy.value, "")
            }
            for strategy in FingerprintStrategy
        ]
    }