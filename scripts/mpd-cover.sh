#!/bin/bash
COVER="/tmp/mpd-cover.png"
PREV_FILE="/tmp/mpd-prev-song"
MUSIC_DIR="${MPD_MUSIC_DIR:-$HOME/Music}"

SONG=$(mpc current --format "%file%" 2>/dev/null)
PREV=$(cat "$PREV_FILE" 2>/dev/null)

if [ "$SONG" != "$PREV" ] || [ ! -s "$COVER" ]; then
    echo "$SONG" > "$PREV_FILE"
    rm -f "$COVER"

    if [ -n "$SONG" ]; then
        SONG_PATH="$MUSIC_DIR/$SONG"
        SONG_DIR=$(dirname "$SONG_PATH")

        for img in "$SONG_DIR/cover.jpg" "$SONG_DIR/cover.png" \
                   "$SONG_DIR/folder.jpg" "$SONG_DIR/folder.png" \
                   "$SONG_DIR/artwork.jpg" "$SONG_DIR/art.jpg" \
                   "$SONG_DIR"/*.jpg "$SONG_DIR"/*.png; do
            if [ -f "$img" ]; then
                ffmpeg -i "$img" -vf "scale=32:32:force_original_aspect_ratio=increase,crop=32:32" \
                    "$COVER" -y -loglevel quiet 2>/dev/null
                break
            fi
        done

        if [ ! -s "$COVER" ]; then
            ffmpeg -i "$SONG_PATH" -an -vframes 1 \
                -vf "scale=32:32:force_original_aspect_ratio=increase,crop=32:32" \
                "$COVER" -y -loglevel quiet 2>/dev/null
        fi
    fi

    if [ ! -s "$COVER" ]; then
        ffmpeg -f lavfi -i "color=#0d0e1c:size=32x32" \
            -vframes 1 "$COVER" -y -loglevel quiet 2>/dev/null
    fi
fi

echo "$COVER"
