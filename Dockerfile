# The report suite as one image (decision 008). At build time the real pipeline turns the synthetic
# sample exports into the pages (September in the store, the nights of Sep 30 to Oct 4, the September
# COO scorecard with its CSV, the month-end close); at run time a thin server only serves reports/.
# Every number in the image comes from synthetic sample data; internal data is simulated and badged.
#
#   docker build -t goodwill-reports .
#   docker run --rm -p 127.0.0.1:8000:8000 goodwill-reports      # then open http://127.0.0.1:8000/
FROM python:3.13-slim

# CLOSE_UPLOADS=0: the image listens on 0.0.0.0 with no authentication, so adding files and re-running the
# close from the portal (decision 010) is off here. Turn it on for a local demo with -e CLOSE_UPLOADS=1.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CLOSE_UPLOADS=0
WORKDIR /app

COPY engine/requirements.txt engine/requirements.txt
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r engine/requirements.txt -r requirements-server.txt

COPY . .
# The PDF step needs Edge, Chrome or Chromium, which the slim image doesn't have: it says so and the
# night goes on. The scorecard page prints to PDF from any browser (one landscape page).
RUN python -m reports.run_scheduled --from 2026-09-30 --to 2026-10-04 \
    && test -f reports/index.html && test -f reports/scorecard/month-2026-09.html

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
# No authentication (decision 006): publish the port to localhost only, as in the run command above.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
