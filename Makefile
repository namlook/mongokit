# sets up the virtual environment
setup: venv/_venv_setup_done venv/_venv_packages_installed

clean:
	rm -rf venv && find . -name "*.pyc" -exec rm -rf {} \;

# run tests
test: pep8 lint utest

utest: setup build
	. venv/bin/activate \
	&& nosetests --where=tests --with-coverage --cover-package=mongokit

lint: setup
	. venv/bin/activate \
	&& pylint --rcfile=.pylintrc ./mongokit

pep8: setup
	. venv/bin/activate \
	&& pep8 --max-line-length=120 mongokit

build: setup
	. venv/bin/activate \
	&& python setup.py clean \
	&& python setup.py install

venv/_venv_setup_done:
	virtualenv --version > /dev/null 2>&1 || pip install --user virtualenv \
	&& virtualenv venv \
	&& touch venv/_venv_setup_done

venv/_venv_packages_installed: requirements.txt
	. venv/bin/activate \
	&& pip install --upgrade pip setuptools \
	&& venv/bin/pip install --download-cache=./.tmp/pip_cache_dir -r requirements.txt --use-mirrors \
	&& touch venv/_venv_packages_installed
