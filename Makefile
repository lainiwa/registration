
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir := $(dir $(mkfile_path))

include .env
export $(shell sed 's/=.*//' .env)

dependencies = docker python3.6 virtualenv npm node gcc sudo wkhtmltoimage lp

b = \033[1m
nb = \033[0m

define help_text

${b}REGISTRATION${nb}

Place the project directory somewhere inside ${b}$$HOME${nb},
for example into ${b}~/projects/registration${nb}.

Then run `${b}make install${nb}` to check for dependencies,
download required libraries, compile website files,
and create a systemd service.

Do ${b}NOT${nb} run from ${b}root${nb}: make will call ${b}sudo${nb} and ask
for password when required (when creating
a ${b}systemd${nb} service).

Commands
├── ${b}help${nb} - print this
├── ${b}install${nb} - install the service
│   ├── ${b}check${nb} - run check before install
│   │   ├── ${b}check-no-root${nb} - check make doesn't run as root
│   │   └── ${b}check-dependencies${nb} - check all required dependencies are installed
│   ├── ${b}frontend${nb} - download node modules and compile frontend
│   │   └── ${b}load-front-deps${nb} - download node modules
│   ├── ${b}set-py-requirements${nb} - create virtual environment for requirements.txt
│   └── ${b}sysd-service${nb} - create systemd daemon
│       └── ${b}unitfile${nb} - write systemd .service file
├── ${b}help${nb} - print this
├── ${b}uninstall${nb} - remove and cleanup stuff
│   └── ${b}clean${nb} - clean files, created with make
├── ${b}db${nb} - run dockerized PostgreSQL
└── ${b}parse${nb} - run parse.py

endef
export help_text

define unitfile_text
[Unit]
Description=Gunicorn instance to serve registration
After=network.target

[Service]
EnvironmentFile=${mkfile_dir}/.env
Type=simple
Restart=on-failure
RestartSec=3
# DefaultStartLimitIntervalSec=0
User=${USER}
Group=${USER}
WorkingDirectory=${mkfile_dir}/backend
Environment='PATH=${mkfile_dir}/backend/venv/bin:/usr/bin:/usr/local/bin:/bin'
ExecStart=${mkfile_dir}/backend/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 main:app

[Install]
WantedBy=multi-user.target
endef
export unitfile_text


.PHONY: help
help:
	echo "$$help_text"


.PHONY: install
install: check frontend set-py-requirements sysd-service

.PHONY: check
check: check-no-root check-dependencies

.PHONY: check-dependencies
check-dependencies:
	$(foreach bin,$(dependencies),\
		$(if $(shell command -v $(bin) 2> /dev/null), \
			 $(info Found `$(bin)`), \
			 $(error Please install `$(bin)`)))

.PHONY: check-no-root
check-no-root:
ifeq "$(USER)" "root"
	$(error This is not intended to be run from root)
else
	$(info The service will be run from user `$(USER)`)
endif

.PHONY: frontend
frontend: load-front-deps
	npm --prefix "${mkfile_dir}/frontend" run build

.PHONY: load-front-deps
load-front-deps:
	npm --prefix "${mkfile_dir}/frontend" install

.PHONY: set-py-requirements
set-py-requirements:
	virtualenv --python=python3.6 "${mkfile_dir}/backend/venv"
	"${mkfile_dir}/backend/venv/bin/pip" install -r "${mkfile_dir}/backend/requirements.txt"

.PHONY: sysd-service
sysd-service: unitfile
	sudo systemctl daemon-reload
	sudo systemctl start registration
	sudo systemctl enable registration

.PHONY: unitfile
unitfile:
	echo "$$unitfile_text" | sudo tee /etc/systemd/system/registration.service >/dev/null


.PHONY: clean
clean:
	rm -rf "${mkfile_dir}/frontend/.cache"
	rm -rf "${mkfile_dir}/frontend/node_modules"
	rm -rf "${mkfile_dir}/backend/venv"
	rm -rf "${mkfile_dir}/backend/__pycache__"
	rm -rf "${mkfile_dir}/backend/parts/__pycache__"
	rm -rf "${mkfile_dir}/backend/resources/rendered*"


.PHONY: uninstall
uninstall: clean
	rm -rf "${mkfile_dir}/frontend/dist"
	sudo systemctl stop registration
	sudo systemctl disable registration
	sudo rm /etc/systemd/system/registration.service
	sudo systemctl daemon-reload
	sudo systemctl reset-failed


.PHONY: db
db: check
	docker run \
		--restart=always \
		--name some-postgres \
		-p 5432:5432 \
		-e POSTGRES_USER=$$DB_USER \
		-e POSTGRES_PASSWORD=$$DB_PASSWORD \
		-d \
		postgres -c 'track_commit_timestamp=on'

.PHONY: parse
parse:
	(cd "${mkfile_dir}/backend/"; env $(cat ../.env | xargs) venv/bin/python parse.py)
