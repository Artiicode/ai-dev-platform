---
target: jetson_agx_orin
---
# Jetson AGX Orin — 접속/배포 정보 (시크릿 금지)
host: 192.168.0.30
user: nvidia
port: 24
deploy_path: /home/nvidia
ssh_key_ref: jetson-orin-key      # 실제 키 아님 — ssh-agent/vault 의 *이름*
arch: aarch64
notes: JetPack 6.2.2 비밀번호/키는 여기 절대 적지 않는다(platform/policies/secrets.md).
