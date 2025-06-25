"""
添加告警模板数据表
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    """升级数据库"""
    op.create_table(
        'alert_templates',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(20), nullable=False, index=True),
        sa.Column('template_type', sa.String(20), nullable=False, index=True),
        
        # 模板内容
        sa.Column('title_template', sa.Text, nullable=False),
        sa.Column('content_template', sa.Text, nullable=False),
        sa.Column('summary_template', sa.Text, nullable=True),
        
        # 模板配置
        sa.Column('template_config', sa.JSON, nullable=True),
        sa.Column('field_mapping', sa.JSON, nullable=True),
        sa.Column('conditions', sa.JSON, nullable=True),
        
        # 兼容性设置
        sa.Column('contact_point_types', sa.JSON, nullable=True),
        sa.Column('severity_filter', sa.JSON, nullable=True),
        sa.Column('source_filter', sa.JSON, nullable=True),
        
        # 元数据
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('is_builtin', sa.Boolean, default=False),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=0),
        
        # 使用统计
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('last_used', sa.DateTime, nullable=True),
        
        # 系统关联
        sa.Column('system_id', sa.Integer, sa.ForeignKey('systems.id'), nullable=True, index=True),
        
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # 创建索引
    op.create_index('ix_alert_templates_category', 'alert_templates', ['category'])
    op.create_index('ix_alert_templates_template_type', 'alert_templates', ['template_type'])
    op.create_index('ix_alert_templates_system_id', 'alert_templates', ['system_id'])
    op.create_index('ix_alert_templates_enabled', 'alert_templates', ['enabled'])
    op.create_index('ix_alert_templates_priority', 'alert_templates', ['priority'])


def downgrade():
    """降级数据库"""
    op.drop_index('ix_alert_templates_priority', 'alert_templates')
    op.drop_index('ix_alert_templates_enabled', 'alert_templates')
    op.drop_index('ix_alert_templates_system_id', 'alert_templates')
    op.drop_index('ix_alert_templates_template_type', 'alert_templates')
    op.drop_index('ix_alert_templates_category', 'alert_templates')
    op.drop_table('alert_templates')