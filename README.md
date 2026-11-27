# Docker Learning
# Turnstile: My First Multi-Container Docker Project

I'm an aspiring DevOps engineer, and this repository is where I documented my first steps with multi-container applications. I started with a few small intro tasks to learn the basics of Docker, then used what I learnt to build a Flask visitor counter backed by Redis and fronted by nginx.

I ran everything inside an **Ubuntu virtual machine using UTM on my Mac**, so this project also taught me a bit about working in a Linux environment.

## Contents

1. [Environment](#environment)
2. [What I built](#what-i-built)
3. [My approach](#my-approach)
4. [Part 1: Intro tasks](#part-1-intro-tasks)
5. [Part 2: The multi-container challenge](#part-2-the-multi-container-challenge)
6. [Notes and debugging steps](#notes-and-debugging-steps)
7. [What I learnt](#what-i-learnt)
8. [Challenges and how I solved them](#challenges-and-how-i-solved-them)
9. [Repository structure](#repository-structure)

---

## Environment

- **Host machine:** Mac
- **Virtualisation:** UTM
- **Guest OS:** Ubuntu <!-- TODO: add version, e.g. 24.04 -->
- **Tools:** Docker and Docker Compose, installed inside the Ubuntu VM <!-- TODO: add versions from `docker --version` and `docker compose version` -->


---

## What I built

**Turnstile** is a visitor counter. Every time someone visits the home page, a counter stored in Redis goes up by one and the visitor gets a numbered "ticket". A second page, `/count`, shows the running total in the same style.

Three containers work together:

```
Browser  -->  nginx (port 5000)  -->  Flask "web" (port 5000)  -->  Redis
              (front door)            (the app)                    (the counter)
```

| Container | Job |
| --- | --- |
| **nginx** | Receives requests from the browser and passes them on to Flask |
| **Flask** | Serves the pages and talks to Redis |
| **Redis** | Stores the visit count |

| Route    | What it does                                                      |
| -------- | ----------------------------------------------------------------- |
| `/`      | Landing page. Increments the counter and shows the visitor ticket |
| `/count` | Shows the total visit count, styled to match the landing page     |

The finished home page, showing visitor number 30:

![Turnstile home page](docs/screenshots/07-home-ticket.png)

---

## My approach

I wanted to understand each concept before combining them, so I worked in stages:

1. **Learn the building blocks.** I first completed the intro tasks: a multi-stage Dockerfile, a Flask app talking to MySQL, and a Compose file to run both.
2. **Reuse the pattern.** For the main challenge I kept the same idea (a Flask app plus a database container) but swapped MySQL for Redis, which suits a counter better.
3. **Add a reverse proxy.** I put nginx in front of Flask to learn how real deployments route traffic.
4. **Keep configuration outside the code.** The Redis host and port come from environment variables, with defaults, so the same code works in different setups.
5. **Debug from the logs.** When something broke, I read `docker compose logs` before changing anything.
6. **Polish last.** Once it worked, I gave the site a name and a theme and styled `/count` to match.

---

## Part 1: Intro tasks

These tasks are in the [`hello_flask`](hello_flask) folder. I completed them first because they teach the ideas the main challenge depends on: building images, connecting containers and using Compose.

### Task 1: Multi-stage Dockerfile

**File:** [`hello_flask/Dockerfile`](hello_flask/Dockerfile)

A multi-stage build uses more than one `FROM` instruction in the same Dockerfile. Mine has two stages:

- **Stage one (build):** starts from `python:3.8-slim`, installs a compiler (`gcc`) and the MariaDB development libraries, copies in the code, and runs `pip install flask mysqlclient`. The `mysqlclient` package has to be compiled, which is why the build tools are needed.
- **Stage two (production):** starts again from a clean `python:3.8-slim`, copies the app across from the first stage with `COPY --from`, exposes port 5000 and runs `python app.py`.

**Why bother?** The compiler and development headers are only useful while installing packages. By leaving them behind in the first stage, the final image is smaller and has less in it that could go wrong.

Build and tag it:

```bash
docker build -t my-flask-app:multistage .
```

<!-- SCREENSHOT: docker build output completing successfully -->
![Multi-stage build output](docs/screenshots/01-multistage-build.png)



### Task 2: Flask app connected to MySQL

**File:** [`hello_flask/app.py`](hello_flask/app.py)

This is a very small Flask app with one route (`/`). When you visit it, the app:

1. Connects to MySQL using `MySQLdb.connect(...)`. The host is `mydb`, which is the name of the database service in Compose.
2. Runs the SQL query `SELECT VERSION()` through a cursor.
3. Returns the result as `Hello, World! MySQL version: ...`.

The point of this app isn't the output. Seeing the MySQL version in the browser proves that **one container can talk to another by name**, which was a big "aha" moment for me.

The password is written directly in the code because this was a practice exercise. I know that in a real project it should come from an environment variable or a secrets manager.

### Task 3: Docker Compose

**File:** [`hello_flask/docker-compose.yml`](hello_flask/docker-compose.yml)

Instead of starting containers one at a time with long `docker run` commands, Compose lets me describe everything in a single YAML file. Mine defines two services:

- **`web`:** runs the `my-flask-app:multistage` image I built in Task 1 and maps port 5000 on the host to port 5000 in the container. `depends_on` tells Compose to start the database first.
- **`mydb`:** runs the official `mysql:8` image. `MYSQL_ROOT_PASSWORD` sets the root password, and it has to match the password in `app.py`.

Compose puts both services on the same network automatically, which is why `app.py` can use `mydb` as a hostname.

Run it from the `hello_flask` folder:

```bash
docker compose up
```

Then visit <http://localhost:5000>.

<!-- SCREENSHOT: docker compose up output with both containers starting -->
![Compose startup](docs/screenshots/03-intro-compose-up.png)

<!-- SCREENSHOT: browser showing "Hello, World! MySQL version: 8.x.x" -->
![Hello World with MySQL version](docs/screenshots/04-intro-hello-mysql.png)

### What the intro tasks taught me

| Task | Concept |
| --- | --- |
| 1 | Keeping images small with multi-stage builds |
| 2 | Containers can reach each other by service name |
| 3 | Compose describes a whole multi-container app in one file |

---

## Part 2: The multi-container challenge

The challenge was to build a Flask app connected to a Redis counter, running as multiple containers. These files are in the [`Challenge`](Challenge) folder.

### The application

**File:** [`Challenge/hello.py`](Challenge/hello.py)

This is a Flask app that uses Redis as its database. Here is how it works:

- **Connecting to Redis:** the host and port come from the environment variables `REDIS_HOST` and `REDIS_PORT`, defaulting to `redis` and `6379`. A Redis client is created once when the app starts.
- **`increment_visits()`:** a helper function that calls `r.incr("visit_count")`. Redis's `INCR` command is atomic, so if two people visit at the same moment, neither increment gets lost. If Redis can't be reached, the function catches the error and returns `None` so the app doesn't crash.
- **The `/` route:** increments the counter and renders the landing page with the visitor's number on a ticket.
- **The `/count` route:** increments the counter and renders the same template with a "Total visits" ticket and a link back home.
- **One shared template:** both pages use the same HTML and CSS through `render_template_string`, so a style change only needs to be made once.
- **Easy customising:** `SITE_NAME`, `TAGLINE` and `ABOUT` at the top of the file control the wording on the site.

I originally returned plain strings from both routes. Turning them into a styled page was a good exercise in separating "get the data" from "show the data".

### The Dockerfile

**File:** [`Challenge/Dockerfile`](Challenge/Dockerfile)

<!-- TODO: adjust to match your Dockerfile (base image, how you install flask and redis, the start command) -->
This builds the image for the Flask container. It starts from a slim Python image, installs the Python packages the app needs (`flask` and `redis`), copies in `hello.py`, exposes port 5000 and starts the app.

### The nginx configuration

**File:** [`Challenge/nginx.conf`](Challenge/nginx.conf)

nginx acts as a **reverse proxy**: it sits in front of Flask, receives requests from the browser and forwards them on. My config is short, so here is what each part does:

- **`events {}`:** nginx requires this block even when it's empty. I left it at the defaults.
- **`upstream flask_app`:** gives a name to the backend. It points at `web:5000`, where `web` is the Flask service name in Compose and `5000` is the port Flask listens on. I used the service name instead of an IP address because Compose's built-in DNS resolves it for me.
- **`listen 5000`:** the port nginx accepts traffic on inside its own container.
- **`location /`:** matches every request and passes it to `flask_app` with `proxy_pass`.

nginx and Flask both use port 5000, but they are separate containers with their own network space, so they don't conflict.

The reason for putting nginx in front is that this is how many real deployments work. nginx is built to handle incoming connections, while Flask's built-in server is only meant for development.



### Docker Compose

**File:** [`Challenge/docker-compose.yml`](Challenge/docker-compose.yml)

<!-- TODO: adjust service names, ports and volumes to match your file -->
This ties everything together. It defines three services on a shared network:

- **`web`** is built from the Dockerfile and gets `REDIS_HOST=redis` so Flask knows where Redis is.
- **`redis`** runs the official Redis image and holds the counter.
- **`nginx`** runs the official nginx image with my `nginx.conf` mounted into it.

### Running it

From the `Challenge` folder:

```bash
docker compose up --build
```

I opened the site in a browser inside the Ubuntu VM, using the address of the container on Docker's network (`172.21.0.3:5000` in my screenshots), which I found with `docker inspect`. Container IPs can change when the stack restarts, so a published port and `localhost` would be more stable.
<!-- TODO: if you re-run with nginx as the only service publishing a port, replace the line above with the URL you use, e.g. http://localhost:5000, and add the curl check from the debugging section -->

Then open:

- `/` for the landing page and visitor ticket
- `/count` for the total visit count



**Home page:** the visitor ticket shows visit number 30.

![Home page with visitor ticket](docs/screenshots/07-home-ticket.png)

**`/count` page:** the next request shows 31, so the counter keeps increasing across both routes.

![Count page](docs/screenshots/08-count-page.png)



---

## Notes and debugging steps

Commands I found useful:

```bash
# See what's running and what has crashed
docker compose ps

# Follow logs for one service
docker compose logs -f web
docker compose logs -f redis
docker compose logs -f nginx

# Check the counter directly in Redis
docker compose exec redis redis-cli GET visit_count

# Test that Flask can reach Redis by name
docker compose exec web python -c "import redis; print(redis.Redis(host='redis').ping())"

# Check the nginx config for syntax errors
docker compose exec nginx nginx -t

# Find a container's IP address on the Docker network
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker compose ps -q)

# Rebuild when something is stale
docker compose down
docker compose up --build

# Clean slate, including volumes and orphaned containers
docker compose down -v --remove-orphans
```
<!-- TODO: change `web`, `redis` and `nginx` above if your service names differ -->

**Checking that traffic goes through nginx.** The `Server:` header in the response shows which program answered:

```bash
curl -I http://localhost:5000
```

`Server: nginx/...` means the request went through the proxy. `Server: Werkzeug/...` means it reached Flask directly.
<!-- TODO: run this and keep only the line that matches what you see. If it shows Werkzeug, make nginx the only service that publishes a port in docker-compose.yml, then re-test. -->

**What I check when it doesn't work**

| Symptom | Likely cause | What to check or do |
| --- | --- | --- |
| `Connection refused` to Redis | Redis isn't running yet, or the wrong host is set | `docker compose ps`; confirm `REDIS_HOST` matches the service name |
| `Name or service not known` | Containers aren't on the same Compose network | Make sure all services are in the same `docker-compose.yml` |
| `localhost` doesn't work for Redis | Inside a container, `localhost` means that container itself | Use the service name instead |
| **502 Bad Gateway** from nginx | nginx can't reach Flask. The `server web:5000` line in `nginx.conf` must match the Flask service name and the port Flask listens on | `docker compose logs nginx web`; check the port in `nginx.conf` against `hello.py` |
| nginx container exits immediately | Syntax error in `nginx.conf` | Read the nginx logs; run `nginx -t` |
| Port already allocated | nginx and Flask both publish host port 5000 | Only the nginx service should publish a port; Flask is reached over the Compose network |
| Flask works directly but not through nginx | Flask must listen on `0.0.0.0`, not just `127.0.0.1` | Check `app.run(host='0.0.0.0', ...)` |
| Page loads but the count shows `?` | Flask is up but Redis isn't reachable | Check the Redis logs and connection settings |
| Code changes don't show up | The image is cached | `docker compose up --build` |
| Site works in the VM but not from my Mac's browser | VM networking | Use the VM's IP address (`ip a` in Ubuntu) instead of `localhost`, and check UTM's network mode |
| `exec format error` or platform warnings | CPU architecture mismatch (ARM vs x86) | Check `uname -m` and prefer images that support `arm64` |
| `my-flask-app:multistage` not found (intro) | Compose uses a pre-built image, not a build step | Run `docker build -t my-flask-app:multistage .` first |
| MySQL `Can't connect` on first start (intro) | MySQL takes a few seconds to initialise, and `depends_on` only waits for the container to *start* | Wait and refresh, or add a healthcheck |

<!-- TODO: keep this note only if you hit this issue, otherwise delete it -->
**Packages missing from the multi-stage image (intro task).** `pip install` puts packages in `site-packages`, but the production stage only copies `/app` from the build stage, so Flask and `mysqlclient` don't make it across. The fix is to install with `pip install --prefix=/install ...` in the build stage and then `COPY --from=build /install /usr/local` in the final stage. The final stage also needs the `libmariadb3` runtime library for `mysqlclient` to load.

<!-- Add your own notes here: the exact error you saw, what you tried, and what finally worked -->

---

## What I learnt

- **Multi-stage builds** keep build tools out of the final image, so it ends up smaller and cleaner.
- **Compose networking:** services reach each other by service name, because Compose gives them DNS on a shared network. `localhost` inside a container only means that container.
- **`depends_on` controls start order, not readiness.** A container can be "started" long before the service inside it is ready.
- **What a reverse proxy does:** nginx receives the traffic and forwards it, so the app doesn't have to face the outside world directly.
- **Containers have their own network space.** nginx and Flask can both use port 5000 without a clash, as long as only one of them publishes that port to the host.
- **Environment variables** let the same code run in different places without editing it.
- **Logs first:** `docker compose logs` answered most of my questions faster than guessing.
- **Working in a Linux VM:** using Ubuntu in UTM gave me practice with the terminal, package installation and VM networking.

<!-- TODO: add anything you personally learnt, in your own words -->

---

## Challenges and how I solved them

<!-- TODO: edit these to reflect what actually happened to you. Delete any that don't apply. -->

**1. Flask couldn't reach the database or Redis.**
I first used the wrong hostname. I fixed it by using the Compose service name (`mydb` or `redis`) instead of `localhost`, then confirmed it with a `ping` from inside the web container.

**2. Making the ports line up.**
At one point my `nginx.conf` used port 5002 while Flask listened on 5000, which meant nginx couldn't reach the app. I changed the upstream and `listen` ports to 5000 so everything agreed.

**3. Code changes didn't appear.**
Docker was reusing a cached image. Running `docker compose up --build` forced a rebuild.

**4. The `/` and `/count` pages looked inconsistent.**
They started as separate pages with different markup. I refactored them into one shared template and a helper function, so the styling and the Redis logic each live in one place.

---


---

## Repository structure

```
.
├── Challenge/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── hello.py
│   └── nginx.conf
├── hello_flask/
│   ├── Dockerfile
│   ├── app.py
│   └── docker-compose.yml
├── docs/
│   └── screenshots/
└── README.md
```
