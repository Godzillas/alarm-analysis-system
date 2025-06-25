"""
添加联络点数据表
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    """升级数据库"""
    op.create_table(
        'contact_points',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('contact_type', sa.String(20), nullable=False, index=True),
        sa.Column('config', sa.JSON, nullable=False),
        sa.Column('enabled', sa.Boolean, default=True),
        
        # 通知设置
        sa.Column('retry_count', sa.Integer, default=3),
        sa.Column('retry_interval', sa.Integer, default=300),
        sa.Column('timeout', sa.Integer, default=30),
        
        # 统计信息
        sa.Column('total_sent', sa.Integer, default=0),
        sa.Column('success_count', sa.Integer, default=0),
        sa.Column('failure_count', sa.Integer, default=0),
        sa.Column('last_sent', sa.DateTime, nullable=True),
        sa.Column('last_success', sa.DateTime, nullable=True),
        sa.Column('last_failure', sa.DateTime, nullable=True),
        
        # 系统关联
        sa.Column('system_id', sa.Integer, sa.ForeignKey('systems.id'), nullable=True, index=True),
        
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # 创建索引
    op.create_index('ix_contact_points_contact_type', 'contact_points', ['contact_type'])
    op.create_index('ix_contact_points_system_id', 'contact_points', ['system_id'])
    op.create_index('ix_contact_points_enabled', 'contact_points', ['enabled'])


def downgrade():
    """降级数据库"""
    op.drop_index('ix_contact_points_enabled', 'contact_points')
    op.drop_index('ix_contact_points_system_id', 'contact_points')
    op.drop_index('ix_contact_points_contact_type', 'contact_points')
    op.drop_table('contact_points')