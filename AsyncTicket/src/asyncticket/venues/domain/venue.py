from dataclasses import dataclass


@dataclass
class Venue:
    """
    공연장 정보를 관리하는 도메인 클래스입니다.
    """

    name: str
    address: str
    address_detail: str
    post_no: str

    venues_id: int | None = None

    def __post_init__(self):
        self.is_valid_name(self.name)

    @classmethod
    def create(
        cls,
        name: str,
        address: str,
        address_detail: str,
        post_no: str,
    ) -> "Venue":
        return cls(
            name=name,
            address=address,
            address_detail=address_detail,
            post_no=post_no,
        )

    def update_info(
        self,
        name: str,
        address: str,
        address_detail: str,
        post_no: str,
    ) -> None:
        self.is_valid_name(name)

        self.name = name
        self.address = address
        self.address_detail = address_detail
        self.post_no = post_no

    @staticmethod
    def is_valid_name(name):
        if not name.strip():
            raise ValueError("공연장명은 비어있을 수 없습니다.")
