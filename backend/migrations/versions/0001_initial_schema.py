"""initial schema: contracts, clauses, chat_messages, risk_results, compare_results

Revision ID: 0001
Revises:
Create Date: 2026-06-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("drive_file_id", sa.String(128), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("contract_type", sa.String(64), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("drive_modified_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("drive_file_id"),
    )
    op.create_index("ix_contracts_drive_file_id", "contracts", ["drive_file_id"])

    op.create_table(
        "clauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("clause_number", sa.String(32), nullable=True),
        sa.Column("clause_title", sa.String(256), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("chroma_chunk_id", sa.String(128), nullable=False),
        sa.UniqueConstraint("chroma_chunk_id"),
    )
    op.create_index("ix_clauses_contract_id", "clauses", ["contract_id"])
    op.create_index("ix_clauses_clause_number", "clauses", ["clause_number"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("question_ar", sa.Text(), nullable=False),
        sa.Column("answer_ar", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_label", sa.String(16), nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    op.create_table(
        "risk_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("rule_key", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("explanation_ar", sa.Text(), nullable=False),
        sa.Column("clause_number", sa.String(32), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_results_contract_id", "risk_results", ["contract_id"])

    op.create_table(
        "compare_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("field_key", sa.String(64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("clause_number", sa.String(32), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_compare_results_contract_id", "compare_results", ["contract_id"])


def downgrade() -> None:
    op.drop_table("compare_results")
    op.drop_table("risk_results")
    op.drop_table("chat_messages")
    op.drop_table("clauses")
    op.drop_table("contracts")
