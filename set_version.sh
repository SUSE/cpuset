#!/bin/bash

VER=${1:?Provide version sring on command line}
DATE=$(TZ=UTC LOCALE=C date '+%B %e, %Y')
DATE_SHORT=$(TZ=UTC LOCALE=C date '+%B %Y')

sed -i "4s/.*/v$VER, $DATE_SHORT/" doc/cset{,-proc,-set,-shield}.txt
sed -i "s/cset v\([[:digit:]]\+\.\)\+[[:digit:]]\+ /cset v$VER /" doc/tutorial.txt
sed -i "s/^\(Version:[[:space:]]*\).*/\1$VER/" cpuset.spec
sed -i "s/^\(version = '*\).*\('[[:space:]]*$\)/\1$VER\2/" cpuset/version.py
sed -i "1i \
============================================================\n\
Cpuset $VER ($DATE)\n\
https://github.com/lpechacek/cpuset\n\
http://download.opensuse.org/repositories/home:/LPechacek:/cpuset-release/\n\
\n
" NEWS
${EDITOR:-vi} NEWS
TEMP=$(mktemp)
sed '6,/^===/{/^=/d;p};d' NEWS > $TEMP
git commit -s -t $TEMP cpuset.spec cpuset/version.py NEWS \
	doc/cset{,-proc,-set,-shield}.txt doc/tutorial.txt
rm -f $TEMP
git tag v$VER
