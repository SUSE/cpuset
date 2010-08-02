PREFIX	?= $(HOME)
DESTDIR	?= /
PYTHON	?= python

all:
	$(PYTHON) setup.py build

rpm:
	$(PYTHON) setup.py bdist_rpm

srcrpm:
	$(PYTHON) setup.py bdist_rpm

srcdist:
	$(PYTHON) setup.py sdist

install:
	$(PYTHON) setup.py install --prefix=$(PREFIX) --root=$(DESTDIR)

test:
	cd t && $(MAKE) all

doc:
	cd doc && $(MAKE) all

clean:
	for dir in doc t; do \
		(cd $$dir && $(MAKE) clean); \
	done
	rm -rf build
	rm -f cpuset/*.pyc
	rm -f cpuset/commands/*.pyc
	rm -f TAGS

clobber: clean
	rm -rf dist

tags:
	ctags -e -R cpuset/*

.PHONY: all install doc test clean
