import os

from sign.sign import DonationKeySigner


dirname = os.path.dirname(__file__)


def test_sign() -> None:
    private_key_path = f"{dirname}/test_privatekey.pem"
    signature = DonationKeySigner(private_key_path).sign("Bitcoin: A Peer-to-Peer Electronic Cash System")

    assert signature == (
        "ZJEwqajrMMajJPjQAfV2T5uMELwo9QhNz3W5IpL3hco+VzO6Wk7bGkP+NqCKB3mB1hmy"
        + "JuiTAAMuz+Q5C6gfdyLYltYFpO0htOG0Hy5j8gXeHcw/sE9kabe0WfqGADozp6TlJOni"
        + "zQ5Gr+ycfE5Muzkj4ryx0Lg6BnDrzf/sfKxCqAU9ezk/JKNNpuPjVgsuCImvQKZrGXCi"
        + "8lt+U/45q3l7PlHJ3YDeo+9Uxlf7AVtfeLAgK4bAYz/VLnQ1CzPswNumkU4XjDXrahhF"
        + "Sojs0P1R16mSwFixpsKA+jbxglZunDX0AO+x8j/rbb5hYf4nZI7bakcFOc9WicizYEa2iQ=="
    )
