FROM python:3.13-slim
RUN pip install --no-cache-dir pytest==9.2.0 pandas==3.1.1 matplotlib==3.11.2 numpy==2.5.4
RUN useradd --uid 1000 --create-home sandbox
USER 1000
WORKDIR /workspace
ENV MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
