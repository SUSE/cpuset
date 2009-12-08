MAN1_TXT=$(wildcard cset*.txt)

DOC_HTML=$(patsubst %.txt,%.html,$(MAN1_TXT) $(MAN7_TXT))

ARTICLES = 
# with their own formatting rules.
SP_ARTICLES = tutorial

DOC_HTML += $(patsubst %,%.html,$(ARTICLES) $(SP_ARTICLES))
DOC_PDF += $(patsubst %,%.pdf,$(ARTICLES) $(SP_ARTICLES))

DOC_MAN1=$(patsubst %.txt,%.1,$(MAN1_TXT))
DOC_MAN7=$(patsubst %.txt,%.7,$(MAN7_TXT))

prefix?=$(HOME)/man
mandir?=$(prefix)
man1dir=$(mandir)/man1
# DESTDIR=

ASCIIDOC=asciidoc --unsafe
ASCIIDOC_EXTRA =
INSTALL?=install

#
# Please note that there is a minor bug in asciidoc.
# The version after 6.0.3 _will_ include the patch found here:
#   http://marc.theaimsgroup.com/?l=git&m=111558757202243&w=2
#
# Until that version is released you may have to apply the patch
# yourself - yes, all 6 characters of it!
#

all: html man

html: $(DOC_HTML)
pdf: $(DOC_PDF)

$(DOC_HTML) $(DOC_MAN1) $(DOC_MAN7): asciidoc.conf

man: man1
man1: $(DOC_MAN1)

install: man
	$(INSTALL) -d -m755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m644 $(DOC_MAN1) $(DESTDIR)$(man1dir)
	cd $(DESTDIR)$(man1dir); gzip *.1

-include doc.dep

clean:
	rm -f *.xml *.pdf doc.dep
	#rm -f *.xml *.html *.pdf *.1 *.7 doc.dep

%.html : %.txt
	$(ASCIIDOC) -b xhtml11 -d manpage -f asciidoc.conf $(ASCIIDOC_EXTRA) $<

%.1 %.7 : %.xml
	xmlto -m callouts.xsl man $<

%.xml : %.txt
	$(ASCIIDOC) -b docbook -d manpage -f asciidoc.conf $<

%.pdf: %.xml
	xmlto pdf $<

#special formatting rules
tutorial.html : %.html : %.txt
	$(ASCIIDOC) -b xhtml11 -d article -f tutorial.conf -a toc -a numbered -a toclevels=4 $(ASCIIDOC_EXTRA) $<
tutorial.xml : %.xml : %.txt
	$(ASCIIDOC) -b docbook -d article -f tutorial.conf $<
