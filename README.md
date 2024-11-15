Up greenhouse app
=================
docker compose -f loki-fundamentals/greenhouse/docker-compose-micro.yml up -d --build

docker compose -f loki-fundamentals/greenhouse/docker-compose-micro.yml restart

docker compose -f loki-fundamentals/greenhouse/docker-compose-micro.yml down

url : localhost:5005


Loki/grafana
=============
hp@hp-HP-Laptop-15s-fq4xxx:~/Documents/loki/loki-fundamentals$ docker compose up -d

hp@hp-HP-Laptop-15s-fq4xxx:~/Documents/loki$ docker compose -f loki-fundamentals/docker-compose.yml down


Grafana-loki Dashboard
======================

Grafana : http://localhost:3000

View Logs via loki
==================

Grafana Home ->  Explore --> Logs ( Choose appropriate label names to narrow down the search

![loki](https://github.com/user-attachments/assets/b7511792-4b30-4336-90c2-a9950a240fc1)
  


