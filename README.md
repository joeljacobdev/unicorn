# unicorn
This is a basic implementation of an ASGI (Asynchronous Server Gateway Interface) web server in Python. It is intended for learning purposes only and should not be used in a production environment.

## ASGI Spec

ASGI is a standard interface between web servers and Python web applications or frameworks. Here are some useful resources to learn more about the ASGI specification:

- [ASGI Specification](https://asgi.readthedocs.io/en/latest/specs/www.html)
- [ASGI Lifespan Specification](https://asgi.readthedocs.io/en/latest/specs/lifespan.html)
- [ASGI Specification in Django](https://django.fun/en/docs/asgiref/3/specs/www/)

## How to Use

You can test the functionality of this web server by using the following endpoints:

- GET request:

`curl -X GET -H "Content-Type: application/json" -d '{"name": "john"}'  "http://0.0.0.0:8000/?suffix=\!\!"`
- OPTIONS request:

`curl -X OPTIONS -H "Content-Type: application/json" -H "Access-Control-Request-Method: GET" -H "Origin: http://0.0.0.0:8000"  -d '{"name": "john"}'  "http://0.0.0.0:8000/?suffix=\!\!"`


## Features

The web server currently supports the following features:

- [x] Handling GET requests
- [x] Handling OPTIONS requests
- [x] Supporting HEAD requests
- [x] Supporting ASGI lifespan start/complete events
- [x] Basic support for multiple worker processes
- [ ] Support for POST and DELETE requests (work in progress)
- [ ] Support for keep-alive connections (pending)
- [ ] Support for Server-Sent Events (SSE) (pending)
- [ ] Support for chunked request and response (pending)

## Contribution

Contributions to this project are welcome. If you want to contribute, please follow the standard open-source practices for submitting pull requests.

## License

This project is licensed under the MIT License. Feel free to use and modify it for your own purposes.