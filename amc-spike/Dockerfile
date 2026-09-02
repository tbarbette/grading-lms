FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# auto-multiple-choice pulls in Perl/GTK deps via apt; texlive-lang-french is
# needed for the "francais" package option used in our test question source.
RUN apt-get update && apt-get install -y --no-install-recommends \
        auto-multiple-choice \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-lang-french \
        poppler-utils \
        sqlite3 \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY wrapper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wrapper/ .

VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
