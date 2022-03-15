PROG=	../../dist/sigtrack
HDRS=	centers.h esig.h exclusions.h queue.h rangelist.h stringlist.h tree.h
OBJS=	centers.o db.o exclusions.o grammar.tab.o lex.yy.o esig.o main.o \
	stringlist.o rangelist.o xls.o
CFLAGS=	-g -O2 -Wall -I../3rdparty/libxlsxwriter/include

$(PROG): $(OBJS)
	gcc $(CFLAGS) -o $(PROG) $(OBJS) \
		../3rdparty/libxlsxwriter/lib/libxlsxwriter.a -lsqlite3 -lz

lex.yy.c:	lex.l grammar.tab.h
	flex lex.l

grammar.tab.h grammar.tab.c:	grammar.y
	bison --defines grammar.y

.c.o:	$(HDRS)
	gcc $(CFLAGS) -c $<

.PHONY:	clean

clean:
	rm -f $(OBJS) $(PROG) lex.yy.c grammar.tab.c grammar.tab.h
