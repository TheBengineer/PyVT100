__author__ = 'WildDoogyPlumb'
import time

class Terminal():
    def __init__(self, width=80, height=24):
        self.width = int(width)
        self.height = int(height)
        self.screen = None
        self.screen_setup()
        self.screen_set_size(width, height)
        self.cursor = [0, 0]
        self.state_buffer = ""
        self.state = 0
        self.command_mode = 0
        self.escape_mode = 0
        self.variable_length_command = 0
        self.shift_mode = 0
        self.printed = 0
        self.last_bell = 0

    # MAIN

    def input(self, stream):
        def done():
            self.command_mode = 0
            self.escape_mode = 0
            self.state_buffer = ""
            self.variable_length_command = 0
            self.printed = 1

        for i, c in enumerate(stream):
            # print i, c, hex(ord(c)), self.escape_mode, self.command_mode, self.variable_length_command, self.cursor
            self.printed = 0
            if self.escape_mode:
                #self.screen_dump()
                #print i, c, hex(ord(c)), self.escape_mode, self.command_mode, self.variable_length_command, self.cursor, self.state_buffer + c
                #for j in self.state_buffer:
                #    print hex(ord(j)),
                #print hex(ord(c))
                #raw_input()
                self.escape_mode += 1
                self.state_buffer += c
                if self.escape_mode == 2:  # First escape Char
                    if c == '[':  # 5B xterm control sequence start
                        self.command_mode = 1
                        continue  # next char
                elif self.escape_mode == 3:  # 2nd escape char
                    if self.state_buffer[-2] == ')':  # Last escape char was ')'
                        if c == '\x30':  # '0' command was ')0': set to G1 Special chars & line set
                            done()
                if self.command_mode:
                    self.command_mode += 1
                    if self.command_mode == 2:
                        if '0' <= c <= '9':  # 30-39 got a value. waiting for command type
                            self.variable_length_command = 1
                        elif c == ';':  # 3B start of 2 piece command
                            self.variable_length_command = 1
                        elif c == '?':  # 3F start of a config command
                            self.variable_length_command = 1
                        elif c == 'H':  # 48  Go to Home/ Set tab at current column
                            self.cursor_send_home()
                            done()
                        elif c == 'J':  # 4A clear below cursor
                            self.screen_clear_below_cursor()
                            done()
                        elif c == 'K':  # Clear screen from cursor right
                            self.screen_clear_line_right()
                            done()
                        elif c == 'm':  # 6D text mode
                            pass  # TODO add text colors
                            done()
                        else:
                            print "Unknmown command code:", hex(ord(c)), c
                            # noinspection PyAssignmentToLoopOrWithParameter
                            for i in self.state_buffer:
                                print i, hex(ord(i))
                    elif self.command_mode >= 3:
                        if not self.variable_length_command:
                            print "Unknmown command code:", hex(ord(c)), c
                            for i in self.state_buffer:
                                print i, hex(ord(i))
                            done()
                    if self.variable_length_command:
                        if '0' <= c <= '9':  # got a value. waiting for command type
                            pass  # Still getting pesky numbers
                        elif c == ';':  # variable separator
                            pass  # Still getting pesky things that are not numbers
                        elif c == '?':  # variable separator
                            pass  # Still getting pesky things that are not numbers
                        elif c == 'J':  # 4A Clear screen
                            if self.state_buffer[-2] == '0':  # 30 Clear screen from cursor down
                                self.screen_clear_below_cursor()
                                done()
                            elif self.state_buffer[-2] == '1':  # 31 Clear screen from cursor up
                                self.screen_clear_above_cursor()
                                done()
                            elif self.state_buffer[-2] == '2':  # 32 Clear entire screen
                                self.screen_clear()
                                done()
                        elif c == 'f':  # 66 Cursor move
                            delim = self.state_buffer.find(';')
                            if not delim == -1:
                                try:
                                    a = int(self.state_buffer[self.state_buffer.find('[') + 1:delim]) - 1
                                except ValueError:
                                    a = 0
                                try:
                                    b = int(self.state_buffer[delim + 1:-1]) - 1
                                except ValueError:
                                    b = 0
                                self.cursor_move_to(b, a)
                                done()
                        elif c == 'm':  # 6D Text Mode
                            pass  # TODO add text colors
                            done()
                        elif c == 'h':  # 68 Text Mode
                            if self.state_buffer[-3] == '?':  # 30 config mode
                                if self.state_buffer[-2] == '3':  # 30 set width to 132
                                    self.screen_set_size(132, self.height)
                            done()
                        elif c == 'l':  # Text Mode
                            if self.state_buffer[-3] == '?':  # 30 config mode
                                if self.state_buffer[-2] == '3':  # 30 set width to 132
                                    self.screen_set_size(80, self.height)
                            done()
                        else:
                            print "Unterminated command (printing):", hex(ord(c)), c
                            for i in self.state_buffer:
                                print i, hex(ord(i))
                            self.put_at_cursor_index(c)
                            done()
            if not self.escape_mode and not self.printed:
                if c == '\x1B':  # 27 escape char
                    self.escape_mode = 1
                    self.state_buffer = '\x1B'
                elif c == '\n':  # 0A new line
                    self.cursor[1] += 1
                    self.cursor_wrap()
                elif c == '\r':  # 0A new line
                    self.cursor[0] = 0
                elif c == '\x0E':  # Shift out
                    self.shift_mode = 1
                elif c == '\x0F':  # Shift in
                    self.shift_mode = 0
                elif c == '\x08':  # backspace
                    self.cursor_move_to(-1, 0, True)
                elif c == '\x07':  # Dell
                    self.last_bell = time.time()
                    print "Beep"
                elif c == '\x00':  # Null
                    pass # Boop
                elif ord(c) <= 31:
                    print "Non printable Character", hex(ord(c)), "at position", self.cursor
                else:
                    self.put_at_cursor_index(c)

    # CURSOR

    def cursor_wrap(self):
        if self.cursor[0] < 0:
            self.cursor[0] = 0
        if self.cursor[0] >= self.width:
            self.cursor[1] += 1
            self.cursor[0] = 0
        if self.cursor[1] < 0:
            self.cursor[1] = 0
        if self.cursor[1] >= self.height:
            self.cursor[1] = 0

    def cursor_send_home(self):
        self.cursor = [0, 0]

    def put_at_cursor(self, c):
        self.cursor_wrap()
        if self.shift_mode:
            if c == 'l' or c == 'm' or c == 'j' or c == 'k':
                c = '+'
            elif c == 'q':
                c = '-'
            elif c == 'x':
                c = '|'
            else:
                print "Strange shifted char:", hex(ord(c)), c
        self.screen[self.cursor[1]][self.cursor[0]] = c

    def put_at_cursor_index(self, c):
        self.cursor_wrap()
        self.put_at_cursor(c)
        self.cursor[0] += 1
        self.cursor_wrap()

    def cursor_move_to(self, x, y, relative=None):
        if not relative:
            self.cursor = [x, y]
        else:
            self.cursor[0] += x
            self.cursor[1] += y
        self.cursor_wrap()  # TODO this might cause issues.

    # SCREEN

    def screen_set_size(self, width, height):
        if height >= 1 and width >= 1:
            self.width = int(width)
            self.height = int(height)
            for index, line in enumerate(self.screen):
                if len(line) > self.width:
                    del line[self.width:]  # What a nice bit of code ^_^
                elif len(line) < self.width:
                    for i in range(len(line), self.width):
                        self.screen[index].append([" "])
            if len(self.screen) > self.height:
                del self.screen[self.height:]  # What a nice bit of code ^_^
            elif len(self.screen) < self.height:
                for i in range(len(self.screen), self.height):
                    self.screen.append([" "] * self.width)
        else:
            print "Terminal size", width, ",", height, "is invalid"

    def screen_setup(self):
        self.screen = [[0]] * self.height
        for index, line in enumerate(self.screen):
            self.screen[index] = [" "] * self.width

    def screen_clear(self):
        self.screen_setup()

    def screen_clear_below_cursor(self):
        self.screen_clear_line_right()
        if self.cursor[1] < self.height:
            for i in range(self.cursor[1] + 1, self.height):
                self.screen[i] = [" "] * self.width

    def screen_clear_above_cursor(self):
        self.screen_clear_line_left()
        if self.cursor[1] > 0:
            for i in range(0, self.cursor[1] - 1):
                self.screen[i] = [" "] * self.width

    def screen_clear_line_right(self):
        if self.cursor[0] < self.width:
            for i in range(self.cursor[0] + 1, self.width):
                self.screen[self.cursor[1]][i] = " "

    def screen_clear_line_left(self):
        if self.cursor[0] > 0:
            for i in range(0, self.cursor[0] - 1):
                self.screen[self.cursor[1]][i] = " "

    def screen_dump(self):
        print "-" * self.width
        for i, line in enumerate(self.screen):
            line_text = ""
            for j, c in enumerate(line):
                if i == self.cursor[1] and j == self.cursor[0]:
                    line_text += '#'
                else:
                    line_text += c
            print line_text.replace('\n', ' ').replace('\n', ' ')
        print "*" * self.width

    # MISC

    def get_char(self, address):
        if self.width > address[0] >= 0 and self.height > address[1] >= 0:
            return self.screen[address[1]][address[0]]
        else:
            print "[ERROR] outside screen", address
            return None

    def get_char_serial(self, position):
        address = (position % self.width, int(position / self.width))
        if self.width > address[0] >= 0 and self.height > address[1] >= 0:
            return self.screen[address[1]][address[0]]
        else:
            print "[ERROR] outside screen", address
            return None

    def get_full_word(self, address):
        address = [address[0], address[1]]
        word = ""
        c = self.get_char(address)
        while c != "" and c != " ":
            address[0] -= 1
            c = self.get_char(address)
        address[0] += 1
        c = self.get_char(address)
        while c != "" and c != " ":
            word += c
            address[0] += 1
            c = self.get_char(address)
        return word

    def get_slice_of_screen(self, address, number_of_chars):
        address = [address[0], address[1]]
        word = ""
        address_serial = (address[1] * self.width) + address[0]
        for i in range(address_serial, address_serial+number_of_chars):
            word += self.get_char_serial(i)
        return word

    def get_word(self, address):
        word = ""
        c = self.get_char(address)
        while c != "" and c != " ":
            word += c
            address[0] += 1
            c = self.get_char(address)
        return word

    def search_string(self, string_to_search):
        assert type(string_to_search) == str
        for index, line in enumerate(self.screen):
            for ind2, char in enumerate(line):
                if char == string_to_search[0]:
                    temp_address = (ind2, index)
                    position = (index * self.width) + ind2
                    for ind3, letter in enumerate(string_to_search):  # Look through word
                        if not self.get_char_serial(position + ind3) == letter:
                            break
                    else:  # Word is complete
                        return temp_address
        # Should not get here, unless the page is fully searched.
        return None

    def search_string_no_case(self, string_to_search):
        assert type(string_to_search) == str
        string_to_search = string_to_search.upper()
        for index, line in enumerate(self.screen):
            for ind2, char in enumerate(line):
                if char == string_to_search[0]:
                    temp_address = (ind2, index)
                    position = (index * self.width) + ind2
                    for ind3, letter in enumerate(string_to_search):  # Look through word
                        if not self.get_char_serial(position + ind3).upper() == letter:
                            break
                    else:  # Word is complete
                        return temp_address

    # CONFIG


