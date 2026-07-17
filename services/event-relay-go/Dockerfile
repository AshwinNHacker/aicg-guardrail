FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.mod .
RUN go mod download || true
COPY . .
RUN go mod tidy && go build -o event-relay .

FROM alpine:3.19
COPY --from=build /app/event-relay /usr/local/bin/event-relay
ENTRYPOINT ["event-relay"]
