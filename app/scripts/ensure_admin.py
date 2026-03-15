from app.services.bootstrap_admin import ensure_seed_admin


def main():
    result = ensure_seed_admin()
    print(result.get("message", "ok"))


if __name__ == "__main__":
    main()
