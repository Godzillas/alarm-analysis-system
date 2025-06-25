"""
添加system_id列到alarms表
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """升级数据库"""
    # 添加 system_id 列到 alarms 表
    op.add_column('alarms', sa.Column('system_id', sa.Integer, nullable=True))
    
    # 创建外键约束
    op.create_foreign_key(
        'fk_alarms_system_id', 
        'alarms', 
        'systems', 
        ['system_id'], 
        ['id']
    )
    
    # 创建索引
    op.create_index('ix_alarms_system_id', 'alarms', ['system_id'])


def downgrade():
    """降级数据库"""
    # 删除索引
    op.drop_index('ix_alarms_system_id', 'alarms')
    
    # 删除外键约束
    op.drop_constraint('fk_alarms_system_id', 'alarms', type_='foreignkey')
    
    # 删除列
    op.drop_column('alarms', 'system_id')