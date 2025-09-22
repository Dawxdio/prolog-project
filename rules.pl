% declarative, logic

:- dynamic previous_board/1.

% Utility: check bounds
on_board(Size, X, Y) :-
    X >= 1, X =< Size,
    Y >= 1, Y =< Size.

% Get adjacent coordinates
adjacent(X, Y, NX, Y) :- NX is X - 1.
adjacent(X, Y, NX, Y) :- NX is X + 1.
adjacent(X, Y, X, NY) :- NY is Y - 1.
adjacent(X, Y, X, NY) :- NY is Y + 1.

% Get stone at a position
get_stone(X, Y, Stones, stone(X, Y, Color)) :-
    member(stone(X, Y, Color), Stones).

% Group finding: collect all connected stones of same color
group(X, Y, Stones, Group) :-
    get_stone(X, Y, Stones, stone(X, Y, Color)),
    group_dfs([(X, Y)], Stones, Color, [], Group).

group_dfs([], _, _, Visited, Visited).
group_dfs([(X, Y)|Rest], Stones, Color, Visited, Group) :-
    member((X, Y), Visited), !,
    group_dfs(Rest, Stones, Color, Visited, Group).
group_dfs([(X, Y)|Rest], Stones, Color, Visited, Group) :-
    findall((NX, NY),
        (adjacent(X, Y, NX, NY),
         get_stone(NX, NY, Stones, stone(NX, NY, Color))),
        Neighbors),
    append(Rest, Neighbors, NextQueue),
    group_dfs(NextQueue, Stones, Color, [(X, Y)|Visited], Group).

% Get liberties of a group
group_liberties([], _, []).
group_liberties([(X, Y)|Rest], Stones, Libs) :-
    findall((NX, NY),
        (adjacent(X, Y, NX, NY),
         \+ member(stone(NX, NY, _), Stones)),
        L),
    group_liberties(Rest, Stones, RestLibs),
    append(L, RestLibs, Combined),
    sort(Combined, Libs).

% Suicide: would this move kill its own group?
is_suicide(X, Y, Color, Stones) :-
    play_move(X, Y, Color, Stones, TempBoard),
    group(X, Y, TempBoard, Group),
    group_liberties(Group, TempBoard, Libs),
    Libs == [].

% Ko rule: prevent repetition of previous state
ko_rule_violated(NewBoard) :-
    previous_board(Prev), sort(Prev, S1), sort(NewBoard, S2), S1 == S2.

% Check legality of a move
legal_move(X, Y, Color, Stones) :-
    \+ is_suicide(X, Y, Color, Stones),
    play_move(X, Y, Color, Stones, NewBoard),
    \+ ko_rule_violated(NewBoard).

% Play move and capture opponent groups
play_move(X, Y, Color, Stones, FinalBoard) :-
    (Color == black -> Opponent = white ; Opponent = black),
    Stones1 = [stone(X, Y, Color)|Stones],
    findall(Group,
        (adjacent(X, Y, NX, NY),
         get_stone(NX, NY, Stones1, stone(NX, NY, Opponent)),
         group(NX, NY, Stones1, Group),
         group_liberties(Group, Stones1, Libs),
         Libs == []),
        GroupsToCapture),
    flatten(GroupsToCapture, Points),
    remove_group(Stones1, Points, FinalBoard).

remove_group(Board, [], Board).
remove_group(Board, [(X, Y)|Rest], NewBoard) :-
    delete(Board, stone(X, Y, _), Temp),
    remove_group(Temp, Rest, NewBoard).

% Store current board state to detect Ko in future
update_ko_history(Board) :-
    retractall(previous_board(_)),
    assertz(previous_board(Board)).

% Basic eye check (all adjacent are same color, and diagonal too)
is_eye(X, Y, Color, Board) :-
    findall((NX, NY), adjacent(X, Y, NX, NY), Neighbors),
    forall(member((NX, NY), Neighbors),
    member(stone(NX, NY, Color), Board)).

% Territory scoring: empty points surrounded by one color
territory_point(X, Y, Board, Size, Owner) :-
    \+ member(stone(X, Y, _), Board),
    explore_territory([(X, Y)], Board, Size, [], Board, Colors),
    sort(Colors, [Owner]).

explore_territory([], _, _, Visited, Visited, []).
explore_territory([(X, Y)|Rest], Board, Size, Visited, Final, Colors) :-
    member((X, Y), Visited), !,
    explore_territory(Rest, Board, Size, Visited, Final, Colors).
explore_territory([(X, Y)|Rest], Board, Size, Visited, Final, ColorsOut) :-
    findall((NX, NY),
        (adjacent(X, Y, NX, NY),
         on_board(Size, NX, NY),
         \+ member(stone(NX, NY, _), Board)),
        NewPoints),
    findall(Color,
        (adjacent(X, Y, NX, NY),
         member(stone(NX, NY, Color), Board)),
        EdgeColors),
    append(Rest, NewPoints, Queue),
    explore_territory(Queue, Board, Size, [(X, Y)|Visited], Final, SubColors),
    append(EdgeColors, SubColors, ColorsOut).

% Calculate total scores (stones + surrounded territory)
total_score(Board, Size, black, Score) :-
    include([stone(_, _, C)]>>(C == black), Board, BlackStones),
    length(BlackStones, StoneScore),
    findall((X,Y),
        (between(1, Size, X), between(1, Size, Y),
         territory_point(X, Y, Board, Size, black)),
        Territory),
    length(Territory, TerritoryScore),
    Score is StoneScore + TerritoryScore.

total_score(Board, Size, white, Score) :-
    include([stone(_, _, C)]>>(C == white), Board, WhiteStones),
    length(WhiteStones, StoneScore),
    findall((X,Y),
        (between(1, Size, X), between(1, Size, Y),
         territory_point(X, Y, Board, Size, white)),
        Territory),
    length(Territory, TerritoryScore),
    Komi is 1.5,
    Score is StoneScore + TerritoryScore + Komi.
