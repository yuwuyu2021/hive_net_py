# HiveNet

A Python-based distributed network system with lightweight server and enhanced client architecture.

## Features

- Lightweight server architecture
- Enhanced client capabilities
- P2P communication
- Distributed storage
- Real-time messaging
- File synchronization
- Remote desktop control
- Screen sharing
- Collaborative editing

## System Requirements

- Python 3.9+
- Git
- PyQt6 (for GUI)

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:yuwuyu2021/hive_net_py.git
   cd hive_net_py
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

```
HiveNet/
├── server/             # Server-side components
│   ├── core/          # Core server functionality
│   ├── handlers/      # Request handlers
│   ├── models/        # Data models
│   └── utils/         # Utility functions
├── client/            # Client-side components
│   ├── gui/           # GUI interface
│   ├── core/          # Core client functionality
│   ├── network/       # Network operations
│   └── utils/         # Utility functions
├── common/            # Shared components
│   ├── protocol/      # Communication protocols
│   ├── security/      # Security modules
│   └── utils/         # Common utilities
├── tests/             # Test cases
└── docs/              # Documentation
```

## Development

1. Create a new feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

3. Push to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

Run tests using pytest:
```bash
pytest tests/
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 