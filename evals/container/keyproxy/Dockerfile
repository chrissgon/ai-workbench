# The key proxy of the eval network (keyproxy.py): it holds the floor model's provider key, so that no run
# container does. evals/executor.py builds it and starts it with the key in its environment, on the internal
# network beside the egress proxy; its calls to the provider leave through that proxy.
FROM alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8
RUN apk add --no-cache python3 ca-certificates \
    && adduser -D -H -s /sbin/nologin keyproxy
COPY keyproxy.py keyproxy.json /etc/keyproxy/
ENV PYTHONDONTWRITEBYTECODE=1
USER keyproxy
EXPOSE 8890
ENTRYPOINT ["python3", "/etc/keyproxy/keyproxy.py"]
