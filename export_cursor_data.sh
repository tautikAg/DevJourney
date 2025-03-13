#!/bin/bash
# Cursor Chat History Exporter and Analyzer - Shell Script Wrapper

# Determine the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Please install Python 3 and try again."
    exit 1
fi

# Make the Python scripts executable if they're not already
if [ ! -x "$SCRIPT_DIR/export_cursor_data.py" ]; then
    chmod +x "$SCRIPT_DIR/export_cursor_data.py"
fi

if [ ! -x "$SCRIPT_DIR/analyze_cursor_data.py" ]; then
    chmod +x "$SCRIPT_DIR/analyze_cursor_data.py"
fi

# Parse arguments
ANALYZE=0
ANALYZE_ARGS=""
EXPORT_ARGS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --analyze)
            ANALYZE=1
            shift
            ;;
        --search)
            ANALYZE=1
            ANALYZE_ARGS="$ANALYZE_ARGS --search \"$2\""
            shift 2
            ;;
        *)
            EXPORT_ARGS="$EXPORT_ARGS $1"
            shift
            ;;
    esac
done

# Run the Python export script with arguments
echo "Running Cursor data export..."
python3 "$SCRIPT_DIR/export_cursor_data.py" $EXPORT_ARGS

# Check if the script executed successfully
if [ $? -ne 0 ]; then
    echo "❌ Error occurred during export. Please check the output above for details."
    exit 1
fi

echo "✅ Cursor data export completed successfully!"

# If analyze flag is set, run the analyzer script
if [ $ANALYZE -eq 1 ]; then
    echo ""
    echo "Running Cursor data analyzer..."
    
    # Find the most recent export directory
    LATEST_EXPORT=$(ls -td "$SCRIPT_DIR"/cursor_data_export_* 2>/dev/null | head -n 1)
    
    if [ -z "$LATEST_EXPORT" ]; then
        echo "No export directory found. Please specify a directory to analyze."
        exit 1
    fi
    
    echo "Analyzing: $(basename "$LATEST_EXPORT")"
    eval "python3 \"$SCRIPT_DIR/analyze_cursor_data.py\" \"$LATEST_EXPORT\" $ANALYZE_ARGS"
    
    if [ $? -eq 0 ]; then
        echo "✅ Cursor data analysis completed successfully!"
    else
        echo "❌ Error occurred during analysis. Please check the output above for details."
        exit 1
    fi
fi

echo ""
echo "All operations completed." 