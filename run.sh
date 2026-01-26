#!/bin/bash
# ChoirOS Docker Runner

set -e

case "${1:-}" in
  dev)
    echo "Starting ChoirOS in development mode..."
    docker-compose up
    ;;
  prod)
    echo "Starting ChoirOS in production mode..."
    docker-compose -f docker-compose.prod.yml up
    ;;
  build)
    echo "Building ChoirOS containers..."
    docker-compose build
    ;;
  stop)
    echo "Stopping ChoirOS..."
    docker-compose down
    docker-compose -f docker-compose.prod.yml down
    ;;
  restart)
    echo "Restarting ChoirOS..."
    $0 stop
    $0 dev
    ;;
  logs)
    docker-compose logs -f
    ;;
  clean)
    echo "Cleaning up ChoirOS..."
    docker-compose down -v
    docker-compose -f docker-compose.prod.yml down -v
    ;;
  *)
    echo "ChoirOS Docker Runner"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  dev       Start development mode (with hot reload)"
    echo "  prod      Start production mode (optimized build)"
    echo "  build     Build the containers"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  logs      Show logs from all services"
    echo "  clean     Stop and remove all containers and volumes"
    echo ""
    echo "Examples:"
    echo "  $0 dev        # Start development environment"
    echo "  $0 prod       # Start production environment"
    echo "  $0 stop       # Stop all services"
    echo ""
    exit 1
    ;;
esac
