#!/usr/bin/env python3
"""Comprehensive command-line interface for the modern banking transfer client."""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from transfer_client.client import BankingClient
from transfer_client.config import Config

# Setup logging
def setup_logging(log_level: str):
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def format_json(data: dict) -> str:
    """Format JSON data for pretty printing."""
    return json.dumps(data, indent=2)


def cmd_transfer(args, client: BankingClient):
    """Execute a transfer command."""
    print(f"\n{'='*60}")
    print(f"💸 Initiating Transfer")
    print(f"{'='*60}")
    print(f"  From Account: {args.from_account}")
    print(f"  To Account:   {args.to_account}")
    print(f"  Amount:       ${args.amount:.2f}")
    print(f"  Using Auth:   {'Yes ✓' if client.config.use_auth else 'No'}")
    print(f"{'='*60}\n")

    result = client.transfer(
        args.from_account,
        args.to_account,
        args.amount,
        use_auth=None if not args.no_auth else False
    )

    if result:
        status = result.get("status", "UNKNOWN")
        if status == "SUCCESS":
            print("✅ Transfer Successful!\n")
            print(f"  Transaction ID: {result.get('transactionId', 'N/A')}")
            print(f"  From Account:   {result.get('fromAccount', 'N/A')}")
            print(f"  To Account:     {result.get('toAccount', 'N/A')}")
            print(f"  Amount:         ${result.get('amount', 0):.2f}")

            if "newFromAccountBalance" in result:
                print(f"  New Balance:    ${result['newFromAccountBalance']:.2f}")

            if "permissionLevel" in result:
                print(f"  Auth Level:     {result['permissionLevel']}")

            if "bonusPoints" in result:
                print(f"\n  🌟 {result['bonusPoints']}")

            return 0
        else:
            print(f"❌ Transfer Failed: {status}\n")
            if "message" in result:
                print(f"  Message: {result['message']}")
            if "fromAccountError" in result:
                print(f"  From Account Error: {result['fromAccountError']}")
            if "toAccountError" in result:
                print(f"  To Account Error: {result['toAccountError']}")
            return 1
    else:
        print("❌ Transfer failed - could not connect to server")
        return 1


def cmd_validate(args, client: BankingClient):
    """Execute account validation command."""
    print(f"\n🔍 Validating Account: {args.account_id}")

    result = client.validate_account(args.account_id)

    if result:
        print(f"\n{format_json(result)}")
        return 0
    else:
        print("\n❌ Validation failed")
        return 1


def cmd_balance(args, client: BankingClient):
    """Execute balance inquiry command."""
    print(f"\n💰 Getting Balance for: {args.account_id}")

    result = client.get_balance(args.account_id)

    if result:
        print(f"\n{format_json(result)}")
        return 0
    else:
        print("\n❌ Failed to get balance")
        return 1


def cmd_accounts(args, client: BankingClient):
    """Execute list all accounts command."""
    print("\n📋 Fetching All Accounts...")

    result = client.get_all_accounts()

    if result:
        # Handle both list and dict response formats
        if isinstance(result, list):
            accounts = result
            print(f"\nFound {len(accounts)} accounts:\n")
            for account in accounts[:args.limit]:
                print(f"  {account.get('id', 'N/A'):8s} - ${account.get('balance', 0):10,.2f}")
            if len(accounts) > args.limit:
                print(f"\n  ... and {len(accounts) - args.limit} more accounts")
        elif isinstance(result, dict):
            # API may return dict with accounts key or dict of accounts
            accounts = result.get('accounts', [])
            if not accounts and 'id' in result:
                # Single account response
                accounts = [result]

            if accounts:
                print(f"\nFound {len(accounts)} accounts:\n")
                for account in list(accounts)[:args.limit]:
                    acc_data = account if isinstance(account, dict) else {"id": str(account), "balance": 0}
                    print(f"  {acc_data.get('id', 'N/A'):8s} - ${acc_data.get('balance', 0):10,.2f}")
                if len(accounts) > args.limit:
                    print(f"\n  ... and {len(accounts) - args.limit} more accounts")
            else:
                # Just print the whole response
                print(f"\n{format_json(result)}")

        return 0
    else:
        print("\n❌ Failed to fetch accounts")
        return 1


def cmd_history(args, client: BankingClient):
    """Execute transaction history command."""
    print(f"\n📊 Fetching Transaction History (limit: {args.limit})...")

    result = client.get_transaction_history(limit=args.limit)

    if result:
        print(f"\n{format_json(result)}")
        return 0
    else:
        print("\n❌ Failed to fetch transaction history")
        return 1


def cmd_interactive(args, client: BankingClient):
    """Start interactive mode."""
    print("\n" + "="*60)
    print("🏦 Banking Client - Interactive Mode")
    print("="*60)
    print("\nAvailable commands:")
    print("  transfer <from> <to> <amount>  - Transfer funds")
    print("  validate <account>             - Validate account")
    print("  balance <account>              - Get account balance")
    print("  accounts [limit]               - List all accounts")
    print("  history [limit]                - Get transaction history")
    print("  help                           - Show this help")
    print("  quit / exit                    - Exit interactive mode")
    print("\n")

    while True:
        try:
            cmd = input("banking> ").strip()

            if not cmd:
                continue

            if cmd in ("quit", "exit"):
                print("\n👋 Goodbye!")
                return 0

            if cmd == "help":
                print("\nAvailable commands:")
                print("  transfer <from> <to> <amount>")
                print("  validate <account>")
                print("  balance <account>")
                print("  accounts [limit]")
                print("  history [limit]")
                print("  help")
                print("  quit / exit\n")
                continue

            parts = cmd.split()
            if not parts:
                continue

            action = parts[0].lower()

            if action == "transfer" and len(parts) == 4:
                from_acc, to_acc, amount = parts[1], parts[2], parts[3]
                try:
                    amount = float(amount)
                    result = client.transfer(from_acc, to_acc, amount)
                    if result and result.get("status") == "SUCCESS":
                        print(f"✅ Transfer successful: {result.get('transactionId')}")
                    else:
                        print(f"❌ Transfer failed: {result.get('message') if result else 'Unknown error'}")
                except ValueError:
                    print("❌ Invalid amount")

            elif action == "validate" and len(parts) == 2:
                result = client.validate_account(parts[1])
                if result:
                    print(f"\n{format_json(result)}")

            elif action == "balance" and len(parts) == 2:
                result = client.get_balance(parts[1])
                if result:
                    print(f"\n{format_json(result)}")

            elif action == "accounts":
                limit = int(parts[1]) if len(parts) > 1 else 10
                result = client.get_all_accounts()
                if result:
                    for account in result[:limit]:
                        print(f"  {account.get('id'):8s} - ${account.get('balance'):10,.2f}")

            elif action == "history":
                limit = int(parts[1]) if len(parts) > 1 else 10
                result = client.get_transaction_history(limit=limit)
                if result:
                    print(f"\n{format_json(result)}")

            else:
                print(f"❌ Unknown command or invalid arguments: {cmd}")
                print("   Type 'help' for available commands")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return 0
        except Exception as e:
            print(f"❌ Error: {e}")


def main() -> None:
    """Main CLI entry point with comprehensive subcommands."""
    parser = argparse.ArgumentParser(
        description="Modern Banking Transfer Client with JWT auth, retry logic, and comprehensive features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple transfer
  transfer-client transfer ACC1000 ACC1001 100.00

  # Transfer without authentication
  transfer-client transfer ACC1000 ACC1001 100.00 --no-auth

  # Validate account
  transfer-client validate ACC1000

  # Get account balance
  transfer-client balance ACC1000

  # List all accounts
  transfer-client accounts --limit 20

  # Get transaction history
  transfer-client history --limit 10

  # Interactive mode
  transfer-client interactive

Environment Variables:
  BANKING_API_URL         - API base URL (default: http://localhost:8123)
  BANKING_USERNAME        - Auth username (default: alice)
  BANKING_PASSWORD        - Auth password (default: password123)
  BANKING_USE_AUTH        - Use JWT auth (default: true)
  BANKING_AUTH_SCOPE      - Auth scope (default: transfer)
  BANKING_LOG_LEVEL       - Log level (default: INFO)
  BANKING_MAX_RETRIES     - Max retry attempts (default: 3)
        """
    )

    parser.add_argument("--config", type=Path, help="Path to config file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    parser.add_argument("--no-auth", action="store_true", help="Disable JWT authentication")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Transfer command
    transfer_parser = subparsers.add_parser("transfer", help="Transfer funds between accounts")
    transfer_parser.add_argument("from_account", help="Source account ID (e.g., ACC1000)")
    transfer_parser.add_argument("to_account", help="Destination account ID (e.g., ACC1001)")
    transfer_parser.add_argument("amount", type=float, help="Amount to transfer")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate an account")
    validate_parser.add_argument("account_id", help="Account ID to validate")

    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Get account balance")
    balance_parser.add_argument("account_id", help="Account ID")

    # Accounts command
    accounts_parser = subparsers.add_parser("accounts", help="List all accounts")
    accounts_parser.add_argument("--limit", type=int, default=10, help="Number of accounts to display")

    # History command
    history_parser = subparsers.add_parser("history", help="Get transaction history")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of transactions")

    # Interactive command
    subparsers.add_parser("interactive", help="Start interactive mode")

    # For backward compatibility: support positional args without subcommand
    parser.add_argument("from_account_compat", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("to_account_compat", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("amount_compat", nargs="?", type=float, help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Load configuration
    config = Config.from_env_or_file(args.config)

    # Override log level if provided
    if args.log_level:
        config.log_level = args.log_level

    # Setup logging
    setup_logging(config.log_level)

    # Create client
    client = BankingClient(config)

    # Handle backward compatibility (no subcommand)
    if not args.command and args.from_account_compat:
        if not args.to_account_compat or args.amount_compat is None:
            parser.error("All three arguments required: from_account, to_account, amount")

        # Fake args for cmd_transfer
        class FakeArgs:
            pass

        fake_args = FakeArgs()
        fake_args.from_account = args.from_account_compat
        fake_args.to_account = args.to_account_compat
        fake_args.amount = args.amount_compat
        fake_args.no_auth = args.no_auth

        sys.exit(cmd_transfer(fake_args, client))

    # Handle subcommands
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to appropriate command handler
    commands = {
        "transfer": cmd_transfer,
        "validate": cmd_validate,
        "balance": cmd_balance,
        "accounts": cmd_accounts,
        "history": cmd_history,
        "interactive": cmd_interactive,
    }

    handler = commands.get(args.command)
    if handler:
        sys.exit(handler(args, client))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
