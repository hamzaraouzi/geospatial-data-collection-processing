import requests
import json
from dotenv import load_dotenv
import os
from typing import str, List
import  pandas as pd
import click
from airflow.providers.google.cloud.hooks.gcs import GCSHook

load_dotenv()
class ProductsFetcher:
    """a class didecated for fetching from sentinel-api."""
    def __init__(self) -> None:
        """construction of the class and initiation of properties."""
        self.catalogue_odata_url = os.getenv("catalogue_odata_url")
        # search parameters
        self.collection_name = os.getenv("collection_name")
        self.product_type = os.getenv("product_type")
        self.session = self._create_download_session()
        self.gcs_hook = GCSHook()

    def _create_download_session(self) -> requests.Session:
        """Create downloading session.

        Returns:
            requests.Session: downloading session.
        """
        username = os.getenv("username")
        password = os.getenv("password")

        # Get authentication token
        auth_server_url = os.getenv("auth_server_url")
        data = {
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        response = requests.post(auth_server_url, data=data, verify=True,
                                 allow_redirects=False)
        try:
            access_token = json.loads(response.text)["access_token"]

        except:
            raise "authantification denied"
        # Establish session
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {access_token}"
        return session

    def _prepare_fetch_query(self, aoi: str,
                             search_period_start: str,
                             search_period_end: str) -> str:
        search_query = f"{self.catalogue_odata_url}/Products?$filter=Collection/Name eq '{self.collection_name}' and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{self.product_type}') and OData.CSC.Intersects(area=geography'SRID=4326;{aoi}') and ContentDate/Start gt {search_period_start} and ContentDate/Start lt {search_period_end}"
        return search_query

    def upload_dataframe_to_storage(self, start_date: str, end_date: str, df: pd.DataFrame) -> str:
        """storing products as csv files to GCS.

        Args:
            start_date (str): starting date of the search period.
            end_date (str): last date  of the search period.
            df (pd.DataFrame): products dataframe.

        Returns:
            str: 
        """
        df.to_csv("/tmp/products.csv")
        self.gcs_hook.upload(bucket_name=os.getenv("bucket_name"),
                             filename="/tmp/products.csv",
                             object_name=f"{start_date}--{end_date}/products.csv")
        return f"{start_date}--{end_date}/products.csv"

    def fetch_products(self, aoi: str, search_period_start: str,
                       search_period_end: str) -> pd.DataFrame:
        search_query = self._prepare_fetch_query(aoi, search_period_start,
                                                 search_period_end)
        response = requests.get(search_query).json()
        result = pd.DataFrame.from_dict(response["value"])
        if len(result) == 0:
            raise "There is no available data to be downloaded"
        return result

    def fetch_aio_coordinates_from_csv(self):
        """fetch coordinates from csv file."""
        self.gcs_hook.download(bucket_name=os.getenv("bucket_name"),
                               object_name="regions.csv",
                               filename="/tmp/regions.csv")
        return pd.read_csv("/tmp/regions.csv")

    def run(self, search_period_start: str, search_period_end: str):
        """data search and download runing func.

        Args:
            search_period_start (str): _description_
            search_period_end (str): _description_

        Returns:
            _type_: _description_
        """
        regions_df = self.fetch_aio_coordinates_from_csv()
        dataframes = []
        for i in range(len(regions_df)):
            aoi = str(regions_df["coodinates"].iloc[i])
            id = str(regions_df["id"].iloc[i])
            df = self.fetch_products(aoi=aoi,
                                     search_period_start=search_period_start,
                                     search_period_end=search_period_end)
            df.assign(region_id=str(id))
            dataframes.append(df)

        dataframe = pd.concat(dataframes)
        return self.upload_dataframe_to_storage(start_date=search_period_start,
                                                end_date=search_period_end,
                                                df=dataframe)


@click.command()
@click.option("--search_period_start", type=str, help="The begining of searching period")
@click.option("--search_period_end", type=str, help="The End of searching period")
def main(search_period_start: str, search_period_end: str):
    """main function, for searching and downloading data.

    Args:
        search_period_start (str): _description_
        search_period_end (str): _description_
    """
    fetcher = ProductsFetcher()
    fetcher.run(search_period_start, search_period_end)