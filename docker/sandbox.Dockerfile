FROM python:3.13-slim
RUN pip install --no-cache-dir pytest pandas matplotlib numpy
RUN useradd --uid 1000 --create-home sandbox
USER 1000
WORKDIR /workspace
ENV MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
