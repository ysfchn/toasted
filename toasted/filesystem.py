from tempfile import TemporaryDirectory, _RandomNameSequence # type: ignore
from typing import Optional, Dict, Union, Iterator
from httpx import Client
from pathlib import Path

class ToastMediaFileSystem():
    """
    Temporary storage for toast notification to use 
    HTTP/HTTPS images in the toast payload.
    """

    def __init__(self) -> None:
        self.fs : TemporaryDirectory = TemporaryDirectory()
        self.fs_path : Path = Path(self.fs.name).resolve()
        self.random_seq : _RandomNameSequence = _RandomNameSequence()
        self.client : Client = Client(
            trust_env = False,
            follow_redirects = True,
            max_redirects = 3
        )
        self.fs_files : Dict[str, str] = {}

    def get_rand_name(self) -> str:
        return next(self.random_seq)

    def create_file(
        self,
        contents : Union[bytes, Iterator[bytes]],
        cache_key : Optional[str] = None
    ) -> str:
        """
        Creates a file in temporary filesystem with given
        content as bytes or an iterator that iterates bytes and
        returns the URI of the created temporary file.
        """
        is_iterator = not isinstance(contents, bytes)
        file_name = self.fs_path / self.get_rand_name()
        with file_name.open("wb") as file:
            if is_iterator:
                for i in contents:
                    file.write(i)
            else:
                file.write(contents)
        path = file_name.resolve().as_uri()
        if cache_key:
            self.fs_files[cache_key] = path
        return path

    def _download_file(
        self, 
        url : str,
        query_params : Optional[Dict[str, str]] = None,
        ignore_fail : bool = True
    ) -> str:
        with self.client.stream(
            method = "GET",
            url = url,
            params = query_params,
            headers = {
                "Range": f"bytes=0-{4 * 1024 * 1024}"
            }
        ) as resp:
            if not resp.is_success:
                if not ignore_fail:
                    resp.raise_for_status()
            # Only allow media smaller than or equal to 3 MB.
            # https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast?tabs=uwp#adding-images
            if int(resp.headers["Content-Length"]) > (3 * 1024 * 1024):
                raise ValueError(f"Remote image cannot be bigger than 3 MB: {url}")
            return self.create_file(resp.iter_bytes(1024), url)

    def get(
        self,
        url : str,
        query_params : Optional[Dict[str, str]] = None,
        ignore_fail : bool = True,
        skip_cache : bool = False
    ) -> str:
        if not skip_cache:
            x = self.fs_files.get(url, None)
            if x:
                return x
        return self._download_file(
            url = url, 
            query_params = query_params, 
            ignore_fail = ignore_fail
        )

    def put(
        self,
        data : Union[bytes, Iterator[bytes]]
    ):
        """
        Creates a temporary file on filesystem with given bytes to use as an 
        media (image or sound) source. In other terms, instead of providing a local 
        file path or a HTTP source to a media, you can provide a bytes object 
        directly using this method. The return value is the created path of the 
        temporary file.

        Parameters:
            data:
                A bytes object or an iterator of bytes.
        """
        return self.create_file(data)


    def close(self):
        self.client.close()
        self.fs_files = {}
        self.fs.cleanup()