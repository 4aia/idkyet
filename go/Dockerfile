# Atlas MCP server - Go build. Replaces deploy/Dockerfile.mcp once the
# REST API side has followed; until then both images can run side by side
# (see the "Status" section in the repo's top-level README).

FROM golang:1.25 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/atlas-mcp ./cmd/atlas-mcp

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/atlas-mcp /atlas-mcp
ENV INFRANODE_MCP_TRANSPORT=streamable-http \
    INFRANODE_MCP_HOST=0.0.0.0 \
    INFRANODE_MCP_PORT=8081
EXPOSE 8081
ENTRYPOINT ["/atlas-mcp"]
