# Documento de Engenharia de Dados: Schemas & Migrations — SpirandeliEmpire OS
**Autor:** Ford, Data Engineer  
**Fase:** 3. Persistência & Dados  
**Status:** Pronto para Aplicação (Ready for Deployment)  
**SGBD Alvo:** PostgreSQL 15+

---

## 1. DDL e Arquitetura Relacional (Schema Core)

Para suportar os requisitos de alta disponibilidade, rastreabilidade e flexibilidade de payload definidos na Arquitetura (Fase 1), o schema foi projetado utilizando UUIDs v4 nativos, colunas de auditoria temporal em `TIMESTAMPTZ` e colunas `JSONB` indexadas para metadados dinâmicos.

### 1.1 Script DDL Principal (`schema_v1.sql`)

```sql
-- Habilita extensão para UUIDs nativos caso necessário
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum para Status de Tarefas
CREATE TYPE task_status_enum AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'cancelled'
);

-- Enum para Roles de Usuário/Agente
CREATE TYPE empire_role_enum AS ENUM (
    'architect',
    'backend_dev',
    'frontend_dev',
    'data_engineer',
    'qa_engineer',
    'devops',
    'admin'
);

-- -----------------------------------------------------------------------------
-- Tabela: users
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role empire_role_enum NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- Tabela: agents
-- -----------------------------------------------------------------------------
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_name VARCHAR(50) UNIQUE NOT NULL,
    role empire_role_enum NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'idle',
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- Tabela: tasks
-- -----------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status task_status_enum NOT NULL DEFAULT 'pending',
    assigned_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_output JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- Tabela: audit_logs (Imutável)
-- -----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    performed_by VARCHAR(100) NOT NULL,
    changes JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 1.2 Triggers de Atualização Automática (`updated_at`)

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 2. Estratégia de Migração (Alembic Script)

Abaixo está o arquivo de migração Python pronto para execução com Alembic (`migrations/versions/0001_initial_schema.py`), garantindo operações reversíveis e seguras (`upgrade` e `downgrade`).

```python
"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-03-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Enums
    task_status = postgresql.ENUM('pending', 'in_progress', 'completed', 'failed', 'cancelled', name='task_status_enum')
    task_status.create(op.get_bind())
    
    empire_role = postgresql.ENUM('architect', 'backend_dev', 'frontend_dev', 'data_engineer', 'qa_engineer', 'devops', 'admin', name='empire_role_enum')
    empire_role.create(op.get_bind())

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM(name='empire_role_enum', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # 3. Agents Table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code_name', sa.String(length=50), nullable=False),
        sa.Column('role', postgresql.ENUM(name='empire_role_enum', create_type=False), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='idle', nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code_name')
    )

    # 4. Tasks Table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM(name='task_status_enum', create_type=False), server_default='pending', nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('result_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('entity_name', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('performed_by', sa.String(length=100), nullable=False),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('tasks')
    op.drop_table('agents')
    op.drop_table('users')
    
    sa.Enum(name='empire_role_enum').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='task_status_enum').drop(op.get_bind(), checkfirst=False)
```

---

## 3. Estratégia de Indexação & Otimização de Consultas

Para evitar *Sequential Scans* em tabelas críticas à medida que a plataforma escala, aplicam-se índices B-Tree e GIN:

```sql
-- Índices B-Tree para Relacionamentos e Queries Frequentes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned_agent ON tasks(assigned_agent_id) WHERE assigned_agent_id IS NOT NULL;
CREATE INDEX idx_tasks_created_by_user ON tasks(created_by_user_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- Índices GIN para Consultas Eficientes em Campos JSONB
CREATE INDEX idx_tasks_payload_gin ON tasks USING gin (payload jsonb_path_ops);
CREATE INDEX idx_agents_capabilities_gin ON agents USING gin (capabilities);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_name, entity_id);
```

---

## 4. Plano de Verificação e Integridade de Dados

| Item de Validação | Comando / Script de Teste | Critério de Aceite |
| :--- | :--- | :--- |
| **Integridade Referencial** | Tentar excluir um `user` com tarefas associadas sem cascading. | Retorno de erro SQLSTATE `23503` (Foreign Key Constraint Violation). |
| **Performance do JSONB** | `EXPLAIN ANALYZE SELECT * FROM tasks WHERE payload @> '{"priority": "high"}';` | Utilização confirmada do `idx_tasks_payload_gin` (Bitmap Index Scan). |
| **Idempotência de Migração** | Executar `alembic upgrade head && alembic downgrade base && alembic upgrade head`. | Transição completa sem erros de objetos pendentes ou duplicados. |
| **Automação de Horário** | `UPDATE users SET name='Ford Test' WHERE email='...';` | Coluna `updated_at` atualizada para o timestamp corrente instantaneamente via trigger. |

---
**Entregável pronto para o Desenvolvedor Core (Balsini) montar os modelos ORM/SQLAlchemy e a suíte de testes (Murphy).**