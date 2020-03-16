# REST API for the Pathways Provider

__REST API providing ReasonerStdAPI access to the Pathways Provider CAM database.__
__Access Swagger UI at `http://HOST:6434/docs`.__

## Installation

### Local Installation

```bash
pip install -r requirements
```

### Docker Installation

```bash
docker build -t cam_api .
```

## Deployment

### Local Deployment

```bash
./main.sh
```

### Docker Deployment

```bash
docker run -p 6434:6434 --name cam_api -d cam_api
```
