OBJS += src/lcn_scanner.o
BIN = bin/_lcn_scanner.so
SWIGS_OBJS = src/lcn_scanner_wrap.o
BIN_DIR = bin

all: clean $(BIN)

$(BIN_DIR):
	mkdir -p $@
	
$(SWIGS_OBJS):
	$(SWIG) -threads -python $(@:_wrap.o=.i)
	$(CC) $(CFLAGS) -c -fpic -o $@ $(@:.o=.c)
	
$(OBJS):
	$(CC) $(CFLAGS) -c -fpic -o $@ $(@:.o=.c)

$(BIN): $(BIN_DIR) $(OBJS) $(SWIGS_OBJS)
	$(CC) $(LDFLAGS) -shared -o $@ $(OBJS) $(SWIGS_OBJS)
	$(STRIP) $@
	
clean:
	rm -f $(OBJS) $(BIN) $(SWIGS_OBJS) src/lcn_scanner_wrap.c src/lcn_scanner.py
	
install:
	install -d $(D)/usr/lib/enigma2/python/Plugins/SystemPlugins/LCNScanner/
	install -m 644 src/*.py $(D)/usr/lib/enigma2/python/Plugins/SystemPlugins/LCNScanner/
	install -m 644 bin/*.so $(D)/usr/lib/enigma2/python/Plugins/SystemPlugins/LCNScanner/
	