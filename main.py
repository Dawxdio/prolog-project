import win32console
import win32file
import win32con
from os import name, system
from pyswip import Prolog

# imperative object-oriented
class board:
    state = None

    def __init__(self, size):
        self.state = [[] for _ in range(size)]
        for i in range(size):
            if i%2==0:
                self.state[i] = ["\033[48;5;173m \033[0m" if a%2==0 else "\033[48;5;130m \033[0m"  for a in range(size)]
            else:
                self.state[i] = ["\033[48;5;130m \033[0m" if a%2==0 else "\033[48;5;173m \033[0m"  for a in range(size)]

    def draw(self):
        clear()
        for i in self.state:
            [print(j*2, end="") for j in i]
            print()
        print("----------", "----------")
        print("|  Pass  |", "| Resign |")
        print("----------", "----------")

    def reset(self, size):
        self.__init__(size)


def clear():
    if name == 'nt':
        system('cls')
    else:
        system('clear')


def get_mouse_input():
    try:
        while True:
            ENABLE_EXTENDED_FLAGS = 0x0080
            ENABLE_QUICK_EDIT_MODE = 0x0040

            win_in = win32console.PyConsoleScreenBufferType(
                win32file.CreateFile("CONIN$",
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    win32file.FILE_SHARE_READ,
                    None,
                    win32file.OPEN_ALWAYS,
                    0,
                    None
                )
            )
            win_in.SetStdHandle(win32console.STD_INPUT_HANDLE)

            in_mode = win_in.GetConsoleMode()
            new_mode = (in_mode | win32console.ENABLE_MOUSE_INPUT | ENABLE_EXTENDED_FLAGS)
            new_mode &= ~ENABLE_QUICK_EDIT_MODE
            win_in.SetConsoleMode(new_mode)
            if len(win_in.PeekConsoleInput(1)) <= 0:
                continue
            event = win_in.ReadConsoleInput(1)[0]

            if event.EventType == win32console.MOUSE_EVENT:
                if event.EventFlags == 0:
                    if (event.ButtonState &
                            win32con.FROM_LEFT_1ST_BUTTON_PRESSED != 0):
                        x = event.MousePosition.X
                        y = event.MousePosition.Y
                        return x, y
    finally:
        win_in.SetConsoleMode(in_mode)


menu_content = {
    "start": ("&" * 24,
              "!        GOLOG          !",
              "!    (Go in Prolog)     !",
              "!  Board size:          !",
              "!  9x9  13x13  19x19    !",
              "&" * 24)
}

# imperative procedural
def draw_start_menu():
    clear()
    for i in menu_content["start"]:
        print(i)
    x, y = get_mouse_input()
    if y == 4:
        if x>=3 and x<=5:
            return 9
        elif x>=8 and x<=12:
            return 13
        elif x>=14 and x<=18:
            return 19
    else:
        return draw_start_menu()
    
# imperative structured
def draw_end_menu(score_b, score_w, col):
    clear()
    for i in board.state:
        [print(j*2, end="") for j in i]
        print()
    winner = "Draw!     "
    if score_b > score_w:
        winner =  "Black Won!"
    elif score_b < score_w:
        winner = "White Won!"
    if col:
        winner = f"{col.capitalize()} Won!"
    str_score_b = str(score_b) + " "*(6-len(str(score_b)))
    str_score_w = str(score_w) + " "*(6-len(str(score_w)))
    print("-"* 25)
    print(f"| Game Over, {winner} |")
    print(f"| Black's score: {str_score_b} |")
    print(f"| White's score: {str_score_w} |")
    print("-" * 25)

def generate_prolog_board(state):
    prolog_board = []
    for y, row in enumerate(state):
        for x, cell in enumerate(row):
            if "#" in cell:  # black stone
                prolog_board.append(f"stone({x+1},{y+1},'black')")
            elif "@" in cell:  # white stone
                prolog_board.append(f"stone({x+1},{y+1},'white')")
    return "[" + ",".join(prolog_board) + "]"


def update_board_from_prolog(prolog_board, size):
    global board
    board.reset(size)
    for term in prolog_board:
        term = term.split(", ")
        x, y, color = int(term[0][6:])-1, int(term[1])-1, term[2][:-1]
        if color == "black":
            sign = "\033[30m#"
        else:
            sign = "\033[38;5;231m@"

        temp = board.state[y][x].split(" ") 
        board.state[y][x] = temp[0]+sign+temp[1]


def main():
    global board
    turn = 0
    size = draw_start_menu()
    board = board(size)
    board.draw()
    prolog = Prolog()
    prolog.consult("rules.pl")
    print("Turn: 1")
    print("Black's turn")
    passes = 0
    resign = False

    while True:
        if turn%2 == 0:
            color = "black"
        else:
            color = "white"
        if passes == 2 or resign:
            print("Calculating final score...")
            score_black = str(list(prolog.query(f"total_score({generate_prolog_board(board.state)},{size}, black, Score)"))[0]["Score"])
            score_white = str(list(prolog.query(f"total_score({generate_prolog_board(board.state)},{size}, white, Score)"))[0]["Score"])
            draw_end_menu(score_black, score_white, color if resign else None)
            exit(0)
        else:
            x, y = get_mouse_input()
            # detect pass and resign button clicks
            if y >= size and y <= size+5:
                if x >= 0 and x <= 9:
                    passes += 1
                    turn += 1
                    board.draw()
                    print(f"{color.capitalize()} passed.")
                    print(f"Turn: {turn+1}")
                    print(f"{'Black' if color == 'white' else 'White'}'s turn")
                    continue
                elif x >= 11 and x <= 20:
                    resign = True
                    print(f"{color.capitalize()} resigned.")
                    turn += 1
                    continue
            passes = 0
            # each tile takes up 2 columns, so need to scale x
            x = x//2

            # check if coordinates are within the board and if the clicked space is empty
            if x >= size or y >= size or " " not in board.state[y][x]:
                continue
            
            prolog_board = generate_prolog_board(board.state)
            query = f"legal_move({x+1}, {y+1}, {color}, {prolog_board})"
            if list(prolog.query(query)):
                move_query = f"play_move({x+1}, {y+1}, {color}, {prolog_board}, NewBoard)"
                result = list(prolog.query(move_query))[0]
                new_board = result["NewBoard"]
                prolog.query(f"update_ko_history({new_board})")
                update_board_from_prolog(new_board, size)
                board.draw()
                turn += 1

                print(f"Turn: {turn+1}")
                print(f"{'Black' if color == 'white' else 'White'}'s turn")
            else:
                print("Illegal move, try again.")

if __name__ == "__main__":
    main()
