"""
This file will contain helper functions for loading, splitting, merging, and embedding documents.
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

def clean_text(text):
    """Replace newlines with spaces unless they indicate a paragraph break."""
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # Replace single newlines with a space
    text = re.sub(r"\n{2,}", "\n\n", text)  # Preserve paragraph breaks
    return text.strip()

def load_pdf(file_path):
    """Load a PDF and clean text per page."""
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    if len(pages) == 0:
        error = Exception(f"Document is empty")
        error.status_code = 400
        raise error
    
    for page in pages:
        page.page_content = clean_text(page.page_content)
    print(f"read {len(pages)} pages from {file_path}")
    return pages

def split_text(pages, min_chars=500):
    """
    Splits text from multiple pages into non-overlapping chunks. Each chunk:
      - Is at least min_chars characters long (except possibly the last chunk),
      - Starts at the beginning of a phrase,
      - Ends at the end of a phrase (i.e. ends with punctuation),
      - And its metadata 'page' is the number of the page where the chunk begins.
    """
    chunks = []
    current_chunk = ""
    current_page_start = None
    page_number = 1

    for page in pages:
        # Split at sentence boundaries or paragraph breaks.
        sentences = re.split(r'(?<=\.)\s|\n\n', page.page_content)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Start a new chunk if necessary.
            if not current_chunk:
                current_chunk = sentence
                current_page_start = page_number
            else:
                current_chunk += " " + sentence

            # If the current chunk is long enough and ends with punctuation, flush it.
            if len(current_chunk) >= min_chars and re.search(r"[.!?](”|')?$", current_chunk):
                chunks.append((current_chunk, {"page": current_page_start}))
                current_chunk = ""
                current_page_start = None

        page_number += 1

    # Append any remaining text as the final chunk.
    if current_chunk:
        chunks.append((current_chunk, {"page": current_page_start}))
 
    return chunks

def compute_cosine_similarity(e1, e2):
    e1 = np.array(e1).reshape(1, -1)
    e2 = np.array(e2).reshape(1, -1)
    sim = cosine_similarity(e1, e2)[0][0]
    return sim

def compute_similarities(embeddings):
    """Compute similarity between each chunk and its right neighbor."""
    #print(f"length of embeddings:", len(embeddings))
    similarities = []
    e1 = np.array(embeddings[0]).reshape(1, -1)
    for i in range(len(embeddings) - 1):
        e2 = np.array(embeddings[i + 1]).reshape(1, -1)
        sim = cosine_similarity(e1, e2)[0][0]
        similarities.append(sim)
        e1 = e2
    avg_inter_similarity = np.mean(similarities)
    #print(f"Length of similarities: ", len(similarities))
    return similarities, avg_inter_similarity

def iterative_merging(chunks, model_name="sentence-transformers/all-mpnet-base-v2"):
    """
    Perform iterative merging until dissimilarity stops improving.
    Uses SentenceTransformer for computing embeddings.
    Chunks are tuples (text, metadata).
    """
    # Extract text for embedding
    texts = [chunk[0] for chunk in chunks]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True)
    similarities, avg_inter_similarity = compute_similarities(embeddings)
    print("Initial average inter chunk similarity:", avg_inter_similarity)

    groups = []
    threshold = 0.95
    average_silhouette = 0

    while len(groups) != 1 and threshold > 0.6:
        last_index = 0
        valid_groups = 0

        while last_index <= len(similarities):  
            i = last_index  # Track current position
            current_group = []  # Start new group
            current_group.append(i)
            
            # Group chunks based on similarity threshold
            while i < len(similarities) and similarities[i] > threshold:
                i += 1  # Move to next similarity entry
                current_group.append(i)

            # Compute average embedding for merged chunks
            complete_text = "".join(chunks[elem][0] for elem in current_group)
            if len(current_group) > 1:
                merged_emb = model.encode(complete_text, convert_to_numpy=True)
            else:
                merged_emb = embeddings[current_group[0]]
            new_chunk = (complete_text, {"page": chunks[current_group[0]][1]['page']})

            # Compute average intra-similarity
            if len(current_group) > 1:
                intra_similarities = [compute_cosine_similarity(embeddings[j], merged_emb) for j in current_group]
                avg_intra_similarity = np.mean(intra_similarities)
                valid_groups += 1
            else:
                avg_intra_similarity = 0.0

            print(f"Average intra-similarity: {avg_intra_similarity}, Group members: {current_group}")
            print(f"Last similarity: {similarities[i]}" if i < len(similarities) else "none")

            groups.append((current_group, new_chunk, merged_emb, avg_intra_similarity))

            # Move to the next ungrouped index
            last_index = i + 1  # Skip merged chunks and start a new group

        # Compute inter-similarity between merged chunks (lower is better)
        new_inter_similarities = []
        for i in range(len(groups)-1):
            new_inter_similarities.append(compute_cosine_similarity(groups[i][2], groups[i + 1][2]))
        new_avg_inter_similarity = np.mean(new_inter_similarities)
        print(f"New average inter-similarity: {new_avg_inter_similarity}, within {len(new_inter_similarities)} groups")

        # Compute average intra-similarity within chunks (higher is better)
        if valid_groups == 0:
            new_avg_intra_similarity = 0
        else:
            new_avg_intra_similarity = sum(group[3] for group in groups) 
            new_avg_intra_similarity /= valid_groups
        print(f"New average intra-similarity: {new_avg_intra_similarity} for {valid_groups} groups")

        if new_avg_intra_similarity !=0:
            new_average_silhouette = (new_avg_intra_similarity - new_avg_inter_similarity) / max(new_avg_intra_similarity, new_avg_inter_similarity)
            if new_average_silhouette <= average_silhouette:
                print("Average silhouette did not improve.")
                break
            else:
                print(f"Average silhouette improved to {new_average_silhouette}")
        print("-"*50)
        similarities = new_inter_similarities
        embeddings = [group[2] for group in groups]
        chunks = [group[1] for group in groups]
        groups = []
        threshold -= 0.1

    return chunks

def generate_final_embeddings(chunks):
    """
    Generate embeddings for text chunks using HuggingFaceEmbeddings.
    Chunks is a list of tuples (text, metadata).
    Returns the HuggingFaceEmbeddings object and a list of embeddings.
    """
    model_name = "sentence-transformers/all-mpnet-base-v2"
    hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)
    final_embeddings = [hf_embeddings.embed_query(chunk[0]) for chunk in chunks]
    return final_embeddings

def semantic_chunking(file_path):
    # Load the source
    try:
        pages = load_pdf(file_path)
    except Exception as e:
        raise
    chunks = split_text(pages)
    print(f"Loaded {len(chunks)} chunks from {file_path}.")
    
    # Generate embeddings
    if len(chunks) == 0:
        error = Exception(f"Document is empty")
        error.status_code = 400
        raise error
    if len(chunks) >1:
        final_chunks = iterative_merging(chunks)
        print(f"Merged into {len(final_chunks)} chunks.")
    else:
        final_chunks = chunks
    if len(final_chunks) < 2:
        error = Exception("Document is too short.")
        error.status_code = 400
        raise error
    final_chunks_embeddings = generate_final_embeddings(final_chunks)
    print(f"Generated embeddings for {len(final_chunks)} chunks.")
    
    # Prepare documents for MongoDB
    documents = []
    for (text, metadata), embedding in zip(final_chunks, final_chunks_embeddings):
        doc = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata  # Stores page number and other relevant metadata
        }
        documents.append(doc)
    
    return documents
