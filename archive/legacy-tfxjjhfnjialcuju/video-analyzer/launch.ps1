$PY = "C:\Program Files\QClaw\v0.2.31.600\resources\python\python.exe"
$APP = "C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\streamlit_app.py"
$WORK = "C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"
Start-Process $PY -ArgumentList "-m streamlit run `"$APP`" --server.port 8501 --server.headless true" -WorkingDirectory $WORK -WindowStyle Hidden
Write-Host "Started"
