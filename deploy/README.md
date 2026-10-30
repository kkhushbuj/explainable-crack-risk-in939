# Deploying to Oracle Cloud next to other projects

The site is a single static page. It runs as **its own small service on its own port** (default 8088),
under its own user, limited to 64 MB of memory and 15% of one CPU. It does not install packages and does
not touch nginx, Apache, Docker, other ports, other files or other firewall rules.

## 1. Look first (read-only)

    ssh -i KEY user@SERVER_IP 'bash -s' < deploy/preflight.sh

This only prints information: what is listening, what is installed, and whether port 8088 is free.

## 2. Open the port in the Oracle console (one-time, in the browser)

Networking, Virtual cloud networks, your VCN, the subnet your server uses, Security Lists, the default list,
Add Ingress Rules: Source CIDR `0.0.0.0/0`, IP Protocol TCP, Destination Port Range `8088`.
Without this rule the site cannot be reached from outside, however well the server is set up.

## 3. Deploy

    bash deploy/deploy.sh user@SERVER_IP /path/to/private-key        # port 8088
    bash deploy/deploy.sh user@SERVER_IP /path/to/private-key 8099   # another port

Then open `http://SERVER_IP:8088/`. Re-running the same command updates the site.
If the port is already used, the script stops before changing anything.

## 4. Undo everything

    ssh -t -i KEY user@SERVER_IP 'sudo bash -s' < deploy/remove.sh

This removes only what this setup created.

## Notes

- The page asks search engines not to index it (`robots.txt` and a meta tag). Anyone with the address can still open it.
- There is no HTTPS without a domain name. Without a domain the address is `http://IP:port/`.
- The site loads fonts and two animation libraries from the internet; visitors need a connection.
