from __future__ import annotations

from insurance_intelligence.benefits.activ_one_nxt_waiting_period_review_packet import (
    write_activ_one_nxt_waiting_period_review_packet,
)


def main() -> None:
    path = write_activ_one_nxt_waiting_period_review_packet()
    print(path)


if __name__ == "__main__":
    main()
