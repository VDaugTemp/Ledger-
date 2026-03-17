"""
Shared loading and chunking for Malaysia Tax Laws data.
Used by ingest.ipynb (vector ingestion) and generate_testset.ipynb (eval test set).
"""
import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from lib.model_provider import ModelProviderSparseEmbeddings

# Paths: ingest_utils.py lives in notebooks/, repo root is parent
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data"

# Chunk settings — same as ingest pipeline so chunks match what's in the vector store
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 400

DOCUMENT_REGISTRY: dict[str, dict] = {
    "income-tax-act-1967-act-53.pdf": {
        "doc_type": "primary_legislation",
        "doc_subtype": "act",
        "title": "Income Tax Act 1967",
        "reference": "Act 53",
        "issuing_body": "Parliament of Malaysia",
        "year": 1967,
        "topics": ["income tax", "general provisions", "assessment", "appeals"],
        "authority_level": 1,
    },
    "Residence_Status_PR_11_2017.pdf": {
        "doc_type": "public_ruling",
        "doc_subtype": "residence",
        "title": "Residence Status of Individuals",
        "reference": "PR 11/2017",
        "issuing_body": "LHDN",
        "year": 2017,
        "topics": ["residence status", "tax residency", "183 days", "individual"],
        "authority_level": 2,
    },
    "Residence_tax_pr-5_2022.pdf": {
        "doc_type": "public_ruling",
        "doc_subtype": "residence",
        "title": "Residence Status of Individuals (Updated)",
        "reference": "PR 5/2022",
        "issuing_body": "LHDN",
        "year": 2022,
        "topics": ["residence status", "tax residency", "individual"],
        "authority_level": 2,
    },
    "Tax_releif_PR2_2012.pdf": {
        "doc_type": "public_ruling",
        "doc_subtype": "tax_relief",
        "title": "Tax Relief for Resident Individual",
        "reference": "PR 2/2012",
        "issuing_body": "LHDN",
        "year": 2012,
        "topics": ["tax relief", "deductions", "resident individual"],
        "authority_level": 2,
    },
    "Tax_treatment_PR8_2011.pdf": {
        "doc_type": "public_ruling",
        "doc_subtype": "employment_income",
        "title": "Tax Treatment of Employee Benefits",
        "reference": "PR 8/2011",
        "issuing_body": "LHDN",
        "year": 2011,
        "topics": ["employment income", "benefits in kind", "perquisites"],
        "authority_level": 2,
    },
    "Abroad_income_20240620-guidelines-tax-treatment-in-relation-to-income-received-from-abroad-amendment-june-2024.pdf": {
        "doc_type": "guidelines",
        "doc_subtype": "foreign_income",
        "title": "Tax Treatment: Income Received from Abroad",
        "reference": "Guidelines June 2024",
        "issuing_body": "LHDN",
        "year": 2024,
        "topics": ["foreign income", "FSI", "remittance", "overseas"],
        "authority_level": 3,
    },
    "tax_incentives_orgs_technical_announcements_250102_1_2.pdf": {
        "doc_type": "technical_announcement",
        "doc_subtype": "tax_incentives",
        "title": "Tax Incentives for Organisations",
        "reference": "Technical Announcement Jan 2025",
        "issuing_body": "LHDN",
        "year": 2025,
        "topics": ["tax incentives", "organisations", "exemptions"],
        "authority_level": 3,
    },
}


def get_file_hash(path: Path) -> str:
    """MD5 fingerprint of file contents — used to detect unchanged files."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def get_splitter() -> RecursiveCharacterTextSplitter:
    """Same splitter as ingest pipeline — paragraph/section-aware for legal text."""
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )


def get_sparse_embedder() -> ModelProviderSparseEmbeddings:
    """Return a BM42 sparse embedder for hybrid ingestion.

    The FastEmbed model (~22 MB) downloads to ~/.cache/fastembed on first call.
    """
    return ModelProviderSparseEmbeddings()


def load_and_chunk_file(
    pdf_path: Path,
    registry_entry: dict,
    splitter: RecursiveCharacterTextSplitter | None = None,
    *,
    source_hash: str | None = None,
) -> list:
    """
    Load one PDF, attach registry metadata to each page, and split into chunks.
    Returns list of LangChain Documents (chunks) with metadata.
    """
    if splitter is None:
        splitter = get_splitter()
    docs = PyPDFLoader(str(pdf_path)).load()
    for doc in docs:
        doc.metadata.update({
            **registry_entry,
            "source_file": pdf_path.name,
            "source_hash": source_hash or "",
            "page": doc.metadata.get("page", 0),
        })
    return splitter.split_documents(docs)


def load_and_chunk_all(
    data_path: Path | None = None,
    registry: dict[str, dict] | None = None,
    splitter: RecursiveCharacterTextSplitter | None = None,
) -> list:
    """
    Load all registered PDFs from data_path, enrich with registry metadata, and chunk.
    Returns a single list of all chunks (same format as in the vector store).
    Use this in generate_testset to get the same chunks as ingest, without Qdrant.
    """
    data_path = data_path or DATA_PATH
    registry = registry or DOCUMENT_REGISTRY
    if splitter is None:
        splitter = get_splitter()
    all_chunks = []
    for pdf_path in sorted(data_path.glob("*.pdf")):
        entry = registry.get(pdf_path.name)
        if not entry:
            continue
        chunks = load_and_chunk_file(pdf_path, entry, splitter)
        all_chunks.extend(chunks)
    return all_chunks
