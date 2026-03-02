import sys
import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QFileDialog,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QMessageBox, QSplitter, QFrame, QScrollArea,
    QTabWidget, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent


class MMseqsWorker(QThread):
    """Worker thread for running MMseqs commands without freezing GUI"""
    output = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        
    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output.emit(line.strip())
            
            self.process.wait()
            self.finished.emit(self.process.returncode)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        if self.process:
            self.process.terminate()


class MMseqsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MMseqs2 GUI - Sequence Analysis Suite")
        self.setGeometry(100, 100, 1400, 900)
        
        # Track current worker
        self.worker = None
        
        # Setup UI
        self.setup_ui()
        self.setup_tool_parameters()
        
        # Apply modern styling
        self.apply_styles()
        
    def setup_ui(self):
        """Initialize the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout with splitter
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Controls (65%)
        left_panel = self.create_left_panel()
        left_panel.setMinimumWidth(400)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(left_panel)
        splitter.addWidget(left_widget)
        
        # Right panel - Output (35%)
        right_panel = self.create_right_panel()
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(right_panel)
        splitter.addWidget(right_widget)
        
        # Set initial sizes to enforce 65/35 split
        splitter.setSizes([910, 490])
        splitter.setHandleWidth(2)
        
        main_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """Create the left control panel"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)  # Reduced from 15
        layout.setContentsMargins(15, 15, 15, 15)  # Reduced from 20
        
        # Header
        header = QLabel("MMseqs2 Control Panel")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # File Selection Group
        file_group = self.create_file_group()
        layout.addWidget(file_group)
        
        # Tool Selection Group
        tool_group = self.create_tool_selection_group()
        layout.addWidget(tool_group)
        
        # Parameters Group (Dynamic)
        self.params_group = QGroupBox("Tool Parameters")
        self.params_layout = QVBoxLayout(self.params_group)
        self.params_layout.setSpacing(0)  # Tight spacing, handled by grid
        self.params_layout.setContentsMargins(10, 15, 10, 10)  # Reduced margins
        layout.addWidget(self.params_group)
        
        # Command Preview
        cmd_group = self.create_command_group()
        layout.addWidget(cmd_group)
        
        # Run Controls
        run_group = self.create_run_group()
        layout.addWidget(run_group)
        
        layout.addStretch()
        scroll.setWidget(container)
        
        # Enable drag and drop
        scroll.setAcceptDrops(True)
        scroll.dragEnterEvent = self.drag_enter_event
        scroll.dropEvent = self.drop_event
        
        return scroll
    
    def create_file_group(self):
        """Create file input section"""
        group = QGroupBox("Input Files")
        layout = QFormLayout()
        layout.setSpacing(6)  # Reduced from 10
        layout.setContentsMargins(10, 15, 10, 10)  # Reduced margins
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Input FASTA
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Select input FASTA file...")
        self.input_path.setReadOnly(True)
        btn_input = QPushButton("Browse...")
        btn_input.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(btn_input)
        layout.addRow("Input FASTA:", input_layout)
        
        # Output Directory
        output_layout = QHBoxLayout()
        output_layout.setSpacing(5)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory...")
        self.output_path.setReadOnly(True)
        btn_output = QPushButton("Browse...")
        btn_output.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(btn_output)
        layout.addRow("Output Dir:", output_layout)
        
        # Database (optional)
        db_layout = QHBoxLayout()
        db_layout.setSpacing(5)
        self.db_path = QLineEdit()
        self.db_path.setPlaceholderText("Select database (optional)...")
        self.db_path.setReadOnly(True)
        btn_db = QPushButton("Browse...")
        btn_db.clicked.connect(self.browse_db)
        db_layout.addWidget(self.db_path)
        db_layout.addWidget(btn_db)
        layout.addRow("Database:", db_layout)
        
        group.setLayout(layout)
        return group
    
    def create_tool_selection_group(self):
        """Create tool selection dropdown"""
        group = QGroupBox("MMseqs Module")
        layout = QVBoxLayout()
        layout.setSpacing(6)  # Reduced spacing
        layout.setContentsMargins(10, 15, 10, 10)  # Reduced margins
        
        self.tool_combo = QComboBox()
        self.tool_combo.addItems([
            "createdb", "search", "cluster", "linclust", 
            "map", "easy-search", "easy-cluster", "easy-linclust",
            "align", "convertalis", "filterdb", "result2profile",
            "profile2consensus", "msa2profile", "expandaln"
        ])
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        
        # Tool description label
        self.tool_desc = QLabel()
        self.tool_desc.setWordWrap(True)
        self.tool_desc.setObjectName("tool-desc")
        
        layout.addWidget(self.tool_combo)
        layout.addWidget(self.tool_desc)
        
        group.setLayout(layout)
        return group
    
    def create_command_group(self):
        """Create command preview section"""
        group = QGroupBox("Generated Command")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 15, 10, 10)
        
        self.cmd_preview = QTextEdit()
        self.cmd_preview.setReadOnly(True)
        self.cmd_preview.setMaximumHeight(80)  # Slightly reduced
        self.cmd_preview.setPlaceholderText("Command will appear here...")
        
        layout.addWidget(self.cmd_preview)
        group.setLayout(layout)
        return group
    
    def create_run_group(self):
        """Create run control buttons"""
        group = QGroupBox("Execution")
        layout = QHBoxLayout()
        layout.setSpacing(8)  # Reduced from default
        layout.setContentsMargins(10, 15, 10, 10)
        
        self.btn_generate = QPushButton("Generate Command")
        self.btn_generate.clicked.connect(self.generate_command)
        self.btn_generate.setObjectName("btn-generate")
        
        self.btn_run = QPushButton("Run MMseqs")
        self.btn_run.clicked.connect(self.run_mmseqs)
        self.btn_run.setObjectName("btn-run")
        self.btn_run.setEnabled(False)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_mmseqs)
        self.btn_stop.setEnabled(False)
        
        layout.addWidget(self.btn_generate)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        
        group.setLayout(layout)
        return group
    
    def create_right_panel(self):
        """Create the right output panel"""
        panel = QFrame()
        panel.setObjectName("right-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins
        layout.setSpacing(8)  # Reduced spacing
        
        # Output header
        header = QLabel("Execution Output")
        header.setObjectName("output-header")
        layout.addWidget(header)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setPlaceholderText("Output will appear here...")
        
        # Progress bar (text-based)
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("progress-label")
        
        layout.addWidget(self.output_text)
        layout.addWidget(self.progress_label)
        
        return panel
    
    def setup_tool_parameters(self):
        """Define parameters for each MMseqs tool"""
        self.tool_params = {
            "createdb": {
                "desc": "Create MMseqs2 database from FASTA file",
                "params": [
                    ("--dbtype", "categorical", {"Automatic detection": 0, "Amino acid": 1, "Nucleotide": 2}, "Database type"),
                    ("--shuffle", "bool", True, "Shuffle input database"),
                    ("--createdb-mode", "categorical", {"Fast (parallel)": 0, "Stable (sequential)": 1}, "Creation mode"),
                ]
            },
            "search": {
                "desc": "Sensitive homology search with profile-to-sequence or sequence-to-sequence comparison",
                "params": [
                    ("-s", "float", "5.7", "Sensitivity (1.0: fast, 5.7: sensitive, 7.5: more sensitive)"),
                    ("-e", "float", "0.001", "E-value threshold"),
                    ("--max-seqs", "int", "300", "Maximum results per query"),
                    ("--max-accept", "int", "1000000", "Maximum accepted alignments"),
                    ("--alignment-mode", "categorical", {"Automatic": 0, "Score only": 1, "Score + end coordinates": 2, "Full alignment": 3}, "Alignment mode"),
                    ("--min-seq-id", "float", "0.0", "Minimum sequence identity (0.0-1.0)"),
                    ("-a", "bool", False, "Add backtrace to alignment (for --format-mode 4)"),
                    ("--cov-mode", "categorical", {"Bidirectional": 0, "Query coverage": 1, "Target coverage": 2}, "Coverage mode"),
                    ("-c", "float", "0.8", "Coverage threshold (0.0-1.0)"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "cluster": {
                "desc": "Cluster sequences using cascaded clustering",
                "params": [
                    ("-s", "float", "5.7", "Sensitivity"),
                    ("-c", "float", "0.8", "Coverage threshold (0.0-1.0)"),
                    ("--cov-mode", "categorical", {"Bidirectional": 0, "Query coverage": 1, "Target coverage": 2}, "Coverage mode"),
                    ("--min-seq-id", "float", "0.0", "Minimum sequence identity (0.0-1.0)"),
                    ("--cluster-mode", "categorical", {"Set cover (greedy)": 0, "Connected component": 1, "Greedy": 2, "Greedy (memory efficient)": 3}, "Cluster mode"),
                    ("--cluster-steps", "int", "3", "Clustering steps"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "linclust": {
                "desc": "Linear time clustering (faster, less sensitive than cluster)",
                "params": [
                    ("-c", "float", "0.9", "Coverage threshold (0.0-1.0)"),
                    ("--kmer-per-seq", "int", "80", "K-mers per sequence"),
                    ("--min-seq-id", "float", "0.9", "Minimum sequence identity (0.0-1.0)"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "map": {
                "desc": "Map reads to reference database (fast mapping)",
                "params": [
                    ("-s", "float", "2.0", "Sensitivity"),
                    ("--min-seq-id", "float", "0.9", "Minimum sequence identity (0.0-1.0)"),
                    ("-c", "float", "0.0", "Coverage threshold (0.0-1.0)"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "easy-search": {
                "desc": "Search query sequences against target database (easy workflow)",
                "params": [
                    ("-s", "float", "5.7", "Sensitivity"),
                    ("-e", "float", "0.001", "E-value threshold"),
                    ("--max-seqs", "int", "300", "Maximum results per query"),
                    ("--alignment-mode", "categorical", {"Automatic": 0, "Score only": 1, "Score + end coordinates": 2, "Full alignment": 3}, "Alignment mode"),
                    ("--format-mode", "categorical", {"BLAST-TAB": 0, "SAM": 2, "BLAST-TAB + lengths": 4}, "Output format"),
                    ("--min-seq-id", "float", "0.0", "Minimum sequence identity (0.0-1.0)"),
                    ("--threads", "int", "4", "Number of threads"),
                    ("--cov-mode", "categorical", {"Bidirectional": 0, "Query coverage": 1, "Target coverage": 2}, "Coverage mode"),
                    ("-c", "float", "0.8", "Coverage threshold (0.0-1.0)"),
                ]
            },
            "easy-cluster": {
                "desc": "Cluster sequences (easy workflow)",
                "params": [
                    ("-s", "float", "5.7", "Sensitivity"),
                    ("-c", "float", "0.8", "Coverage threshold (0.0-1.0)"),
                    ("--min-seq-id", "float", "0.0", "Minimum sequence identity (0.0-1.0)"),
                    ("--cov-mode", "categorical", {"Bidirectional": 0, "Query coverage": 1, "Target coverage": 2}, "Coverage mode"),
                    ("--cluster-mode", "categorical", {"Set cover (greedy)": 0, "Connected component": 1, "Greedy": 2, "Greedy (memory efficient)": 3}, "Cluster mode"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "easy-linclust": {
                "desc": "Linear time clustering (easy workflow)",
                "params": [
                    ("-c", "float", "0.9", "Coverage threshold (0.0-1.0)"),
                    ("--min-seq-id", "float", "0.9", "Minimum sequence identity (0.0-1.0)"),
                    ("--kmer-per-seq", "int", "80", "K-mers per sequence"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "align": {
                "desc": "Compute alignments for previous search results",
                "params": [
                    ("-e", "float", "0.001", "E-value threshold"),
                    ("--alignment-mode", "categorical", {"Automatic": 0, "Score only": 1, "Score + end coordinates": 2, "Full alignment": 3}, "Alignment mode"),
                    ("--min-seq-id", "float", "0.0", "Minimum sequence identity (0.0-1.0)"),
                    ("-a", "bool", False, "Add backtrace"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "convertalis": {
                "desc": "Convert alignment database to BLAST-TAB or other formats",
                "params": [
                    ("--format-mode", "categorical", {"BLAST-TAB": 0, "SAM": 2, "BLAST-TAB + lengths": 4}, "Format mode"),
                    ("--format-output", "str", "", "Custom output format string"),
                ]
            },
            "filterdb": {
                "desc": "Filter a database by condition",
                "params": [
                    ("--filter-column", "int", "1", "Column to filter on"),
                    ("--filter-regex", "str", "", "Regex filter"),
                    ("--filter-file", "str", "", "File with entries to filter"),
                    ("--positive-filter", "bool", True, "Positive filtering (keep matches)"),
                ]
            },
            "result2profile": {
                "desc": "Convert alignment result to profile database",
                "params": [
                    ("--e-profile", "float", "0.1", "E-value threshold for profile"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "profile2consensus": {
                "desc": "Convert profile database to consensus sequence database",
                "params": [
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "msa2profile": {
                "desc": "Convert MSA to profile database",
                "params": [
                    ("--match-mode", "categorical", {"Gap fraction": 0, "Auto": 1}, "Match mode"),
                    ("--match-ratio", "float", "0.5", "Match ratio threshold (0.0-1.0)"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            },
            "expandaln": {
                "desc": "Expand alignments by transitive alignment",
                "params": [
                    ("--expansion-mode", "categorical", {"Default": 0, "Keep all hits": 1, "Keep best hits": 2}, "Expansion mode"),
                    ("--threads", "int", "4", "Number of threads"),
                ]
            }
        }
        
        # Initialize with first tool
        self.on_tool_changed("createdb")
    
    def on_tool_changed(self, tool_name):
        """Update parameter panel when tool selection changes"""
        # Clear existing parameters
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Update description
        if tool_name in self.tool_params:
            self.tool_desc.setText(self.tool_params[tool_name]["desc"])
            
            # Create parameter inputs using grid layout for better alignment
            params = self.tool_params[tool_name]["params"]
            
            # Create a widget to hold the grid
            grid_widget = QWidget()
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setSpacing(8)  # Consistent spacing between rows and columns
            grid_layout.setContentsMargins(5, 5, 5, 5)
            grid_layout.setColumnStretch(0, 0)  # Label column doesn't stretch
            grid_layout.setColumnStretch(1, 1)  # Input column stretches
            
            self.param_widgets = {}
            
            for row, param in enumerate(params):
                param_name = param[0]
                param_type = param[1]
                
                # Create label
                label = QLabel()
                label.setWordWrap(True)
                label.setMinimumWidth(180)
                label.setMaximumWidth(250)
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                
                if param_type == "categorical":
                    options_dict = param[2]
                    description = param[3]
                    
                    widget = QComboBox()
                    widget.setMinimumWidth(200)
                    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    
                    # Store mapping from description to value
                    self.param_widgets[param_name] = (widget, "categorical", options_dict)
                    
                    # Add items with descriptions
                    for desc, val in options_dict.items():
                        widget.addItem(desc, val)
                    
                    widget.setCurrentIndex(0)
                    
                    label_text = f"{param_name}\n[{description}]"
                    label.setText(label_text)
                    label.setToolTip(f"Type: categorical\n{description}")
                    
                elif param_type == "bool":
                    default_val = param[2]
                    description = param[3]
                    
                    widget = QCheckBox()
                    widget.setChecked(default_val)
                    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    
                    self.param_widgets[param_name] = (widget, "bool", None)
                    
                    label_text = f"{param_name}\n[boolean]"
                    label.setText(label_text)
                    label.setToolTip(f"Type: boolean\n{description}")
                    
                else:
                    # int, float, str - use simple text input
                    default_val = param[2]
                    description = param[3]
                    
                    widget = QLineEdit()
                    widget.setText(str(default_val))
                    widget.setPlaceholderText(str(default_val))
                    widget.setMinimumWidth(200)
                    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    
                    self.param_widgets[param_name] = (widget, param_type, None)
                    
                    type_label = param_type
                    label_text = f"{param_name}\n[{type_label}]"
                    label.setText(label_text)
                    label.setToolTip(f"Type: {param_type}\n{description}")
                
                # Set fixed height for consistency
                label.setMinimumHeight(40)
                widget.setMinimumHeight(28)
                
                # Add to grid with alignment
                grid_layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                grid_layout.addWidget(widget, row, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            self.params_layout.addWidget(grid_widget)
        
        self.generate_command()
    
    def browse_input(self):
        """Browse for input FASTA file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input FASTA", "", 
            "FASTA files (*.fa *.fasta *.faa *.fna *.fa.gz *.fasta.gz);;All files (*)"
        )
        if file_path:
            self.input_path.setText(file_path)
            # Auto-set output if not set
            if not self.output_path.text():
                default_out = os.path.join(os.path.dirname(file_path), "mmseqs_output")
                self.output_path.setText(default_out)
    
    def browse_output(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_path.setText(dir_path)
    
    def browse_db(self):
        """Browse for database"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Database", "",
            "MMseqs DB (*.dbtype);;All files (*)"
        )
        if file_path:
            self.db_path.setText(file_path)
    
    def drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def drop_event(self, event: QDropEvent):
        """Handle file drop"""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith(('.fa', '.fasta', '.faa', '.fna', '.fa.gz', '.fasta.gz')):
                self.input_path.setText(file_path)
                if not self.output_path.text():
                    default_out = os.path.join(os.path.dirname(file_path), "mmseqs_output")
                    self.output_path.setText(default_out)
    
    def generate_command(self):
        """Generate MMseqs command based on current inputs"""
        tool = self.tool_combo.currentText()
        input_file = self.input_path.text()
        output_dir = self.output_path.text()
        db_file = self.db_path.text()
        
        if not input_file and tool in ["createdb", "easy-search", "easy-cluster", "easy-linclust"]:
            self.cmd_preview.setText("Please select input file first")
            self.btn_run.setEnabled(False)
            return
        
        if not output_dir:
            self.cmd_preview.setText("Please select output directory")
            self.btn_run.setEnabled(False)
            return
        
        # Build command
        cmd_parts = ["mmseqs", tool]
        
        # Add input/output based on tool type
        if tool.startswith("easy-"):
            # Easy tools take FASTA directly
            cmd_parts.append(f'"{input_file}"')
            if db_file:
                cmd_parts.append(f'"{db_file}"')
            else:
                cmd_parts.append(f'"{output_dir}/result"')
            cmd_parts.append(f'"{output_dir}"')
        elif tool == "createdb":
            cmd_parts.append(f'"{input_file}"')
            cmd_parts.append(f'"{output_dir}/db"')
        elif tool in ["search", "map"]:
            if db_file:
                cmd_parts.append(f'"{output_dir}/query_db"')
                cmd_parts.append(f'"{db_file}"')
            else:
                cmd_parts.append(f'"{input_file}"')
                cmd_parts.append(f'"{output_dir}/target_db"')
            cmd_parts.append(f'"{output_dir}/result"')
            cmd_parts.append(f'"{output_dir}/tmp"')
        elif tool in ["cluster", "linclust"]:
            cmd_parts.append(f'"{output_dir}/db"')
            cmd_parts.append(f'"{output_dir}/cluster"')
            cmd_parts.append(f'"{output_dir}/tmp"')
        else:
            cmd_parts.append(f'"{input_file}"')
            cmd_parts.append(f'"{output_dir}/output"')
        
        # Add parameters
        if hasattr(self, 'param_widgets'):
            for param_name, (widget, param_type, mapping) in self.param_widgets.items():
                if param_type == "bool":
                    if widget.isChecked():
                        cmd_parts.append(param_name)
                elif param_type == "categorical":
                    # Get the actual integer value from the mapping
                    current_desc = widget.currentText()
                    actual_value = widget.currentData()
                    cmd_parts.append(f"{param_name} {actual_value}")
                else:
                    # int, float, str - just get text value
                    val = widget.text().strip()
                    if val:  # Only add if not empty
                        cmd_parts.append(f"{param_name} {val}")
        
        command = " ".join(cmd_parts)
        self.cmd_preview.setText(command)
        self.btn_run.setEnabled(True)
        
        return command
    
    def run_mmseqs(self):
        """Execute the generated command"""
        command = self.cmd_preview.toPlainText()
        
        if not command or command.startswith("Please"):
            QMessageBox.warning(self, "Error", "Please generate a valid command first")
            return
        
        # Clear previous output
        self.output_text.clear()
        self.output_text.append(f"$ {command}\n")
        self.output_text.append("Starting MMseqs2 execution...\n")
        
        # Update UI state
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_label.setText("Running...")
        
        # Start worker thread
        self.worker = MMseqsWorker(command)
        self.worker.output.connect(self.append_output)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def append_output(self, text):
        """Append text to output area"""
        self.output_text.append(text)
        # Auto-scroll
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_finished(self, return_code):
        """Handle command completion"""
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        
        if return_code == 0:
            self.progress_label.setText("Completed successfully")
            self.output_text.append("\n✓ Execution completed successfully")
        else:
            self.progress_label.setText(f"Failed (code: {return_code})")
            self.output_text.append(f"\n✗ Execution failed with code: {return_code}")
    
    def on_error(self, error_msg):
        """Handle execution error"""
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_label.setText("Error occurred")
        self.output_text.append(f"\nError: {error_msg}")
        QMessageBox.critical(self, "Execution Error", error_msg)
    
    def stop_mmseqs(self):
        """Stop running process"""
        if self.worker:
            self.worker.stop()
            self.progress_label.setText("Stopped by user")
            self.output_text.append("\n⚠ Execution stopped by user")
            self.btn_run.setEnabled(True)
            self.btn_stop.setEnabled(False)
    
    def apply_styles(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #dcdde1;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                background-color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 8px;
                color: #2f3640;
                background-color: white;
            }
            
            #header {
                font-size: 22px;
                font-weight: bold;
                color: #2f3640;
                padding: 8px;
                margin-bottom: 5px;
            }
            
            #tool-desc {
                color: #718093;
                font-style: italic;
                padding: 6px;
                background-color: #f8f9fa;
                border-radius: 4px;
                margin-top: 5px;
                font-size: 11px;
            }
            
            QPushButton {
                background-color: #487eb0;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 70px;
                font-size: 11px;
            }
            
            QPushButton:hover {
                background-color: #40739e;
            }
            
            QPushButton:pressed {
                background-color: #487eb0;
            }
            
            QPushButton:disabled {
                background-color: #dcdde1;
                color: #7f8fa6;
            }
            
            #btn-run {
                background-color: #44bd32;
            }
            
            #btn-run:hover {
                background-color: #4cd137;
            }
            
            #btn-generate {
                background-color: #e1b12c;
            }
            
            #btn-generate:hover {
                background-color: #fbc531;
            }
            
            QLineEdit {
                padding: 4px 6px;
                border: 1px solid #dcdde1;
                border-radius: 3px;
                background-color: white;
                min-height: 24px;
                font-size: 11px;
            }
            
            QLineEdit:focus {
                border-color: #487eb0;
                border-width: 2px;
            }
            
            QComboBox {
                padding: 4px 6px;
                border: 1px solid #dcdde1;
                border-radius: 3px;
                background-color: white;
                min-height: 24px;
                font-size: 11px;
            }
            
            QComboBox:focus {
                border-color: #487eb0;
                border-width: 2px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            
            QComboBox QAbstractItemView {
                border: 2px solid #dcdde1;
                selection-background-color: #487eb0;
            }
            
            QCheckBox {
                spacing: 6px;
                min-height: 24px;
                font-size: 11px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #dcdde1;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #487eb0;
                border-color: #487eb0;
            }
            
            QTextEdit {
                border: 2px solid #dcdde1;
                border-radius: 4px;
                background-color: #2f3640;
                color: #f5f6fa;
                padding: 8px;
                font-size: 11px;
            }
            
            #right-panel {
                background-color: #2f3640;
                border-left: 2px solid #487eb0;
            }
            
            #output-header {
                color: #f5f6fa;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }
            
            #progress-label {
                color: #f5f6fa;
                padding: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            
            QLabel {
                color: #2f3640;
                font-size: 10px;
                line-height: 1.2;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
            }
        """)


def main():
    app = QApplication(sys.argv)
    
    # Set application font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = MMseqsGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
