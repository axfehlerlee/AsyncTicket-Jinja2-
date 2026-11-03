class Venues:
    """
    공연장 정보를 관리하는 도메인 클래스입니다.
    """

    def __init__(self, id:int, name:str, address:str, address_detail:str, post_no:str):
        if name:
            raise ValueError("이름은 비어있을 수 없습니다.")

        self.id = id
        self.name = name
        self.address = address
        self.address_detail = address_detail
        self.post_no = post_no

