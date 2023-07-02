# unicorn

curl -X GET http://0.0.0.0:8000/
curl -X GET -H "Content-Type: application/json" -d '{"name": "john"}'  "http://0.0.0.0:8000/?suffix=\!\!"
curl -X OPTIONS -H "Content-Type: application/json" -H "Access-Control-Request-Method: GET" -H "Origin: http://0.0.0.0:8000"  -d '{"name": "john"}'  "http://0.0.0.0:8000/?suffix=\!\!"

## ASGI Spec
- https://asgi.readthedocs.io/en/latest/specs/www.html
- https://django.fun/en/docs/asgiref/3/specs/www/

## TODO
- [ ] when is receive() called?
- [ ] when is disconnect called?
- [ ] support/test POST/DELETE
- [x] test/support HEAD/OPTIONS
- [x] support lifecycle start/complete
- [x] basic multiple worker support
- [ ] handling of signals and cleanup
- [ ] support keep alive
- [ ] support SSE
- [ ] support chunked request and response