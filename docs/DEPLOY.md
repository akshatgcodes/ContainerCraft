# Deploy

## Website

The product page at **https://containercraft.akshatgcodes.in** is `landing/` (a Next.js static export) on Vercel, connected to this repo. ContainerCraft itself is a CLI and runs on your machine; the rest of this page is about that.

ContainerCraft runs **on the Docker host it manages**; it isn't a hosted web app.

## As a service (Linux, systemd)

```ini
# /etc/systemd/system/containercraft.service
[Unit]
Description=ContainerCraft API
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/opt/containercraft
Environment=CRAFT_API_KEY=<long random value>
Environment=CRAFT_MONITOR=true
Environment=CRAFT_AUTO_RESTART=true
ExecStart=/usr/local/bin/uv run uvicorn containercraft.api:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

The user running it needs access to the Docker socket (the `docker` group), which is effectively root on that host.

## Exposure

- Keep `--host 127.0.0.1`. If remote access is needed, put it behind a reverse proxy with TLS, or use an SSH tunnel.
- Always set `CRAFT_API_KEY` when the API is reachable by anything other than you.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
