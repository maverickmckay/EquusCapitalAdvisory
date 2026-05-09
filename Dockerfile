FROM python:3.11-slim

# System dependencies for document parsing and optional LaTeX
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    poppler-utils \
    antiword \
    && rm -rf /var/lib/apt/lists/*

# Optional: uncomment to install LaTeX for PDF compilation
# RUN apt-get update && apt-get install -y texlive-latex-base texlive-fonts-recommended latexmk \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/projects

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
