import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point, LineString


def clean_empty(gdf):
    gdf = gdf.loc[~gdf.geometry.is_empty, :]
    prior = len(gdf)
    gdf = gdf.loc[~gdf.geometry.isna(), :]
    post = len(gdf)
    print(prior - post, 'geoms emtpy or nan removed')
    return gdf


def clean_duplicates(gdf):
    duplicated_parcels = gdf.geometry.map(lambda g: g.wkb.hex()).duplicated()
    print('There are %i duplicated parcels' % duplicated_parcels.sum())
    gdf = gdf.loc[~duplicated_parcels, :]
    return gdf


def extract_poly_from_collection(indf):
    is_simple = indf.geometry.map(is_polygon)
    indf_simple = indf.loc[is_simple, :].copy()
    indf_multi = indf.loc[~is_simple, :].copy()

    outdf = gpd.GeoDataFrame(columns=indf_multi.columns)
    for idx, row in indf_multi.iterrows():
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row] * recs, ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom, 'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf, ignore_index=True)

        elif type(row.geometry) == GeometryCollection:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            for geom in row.geometry:
                if (type(geom) == Polygon) | (type(geom) == MultiPolygon):
                    gdf_coll = gpd.GeoDataFrame(columns=indf.columns)
                    gdf_coll = gdf_coll.append([row], ignore_index=True)
                    gdf_coll.loc[0, 'geometry'] = geom
                    multdf = multdf.append(gdf_coll)
            outdf = outdf.append(multdf, ignore_index=True)
    outdf = outdf.append(indf_simple)
    outdf = outdf.reset_index(drop=True)
    return outdf


def from_multy_to_poly(gdf):
    gdf.geometry = gdf.geometry.map(multy_to_poly)
    gdf = extract_poly_from_collection(gdf)
    return gdf


def get_first_poly(g):
    return g[0]


def is_multypolygon(g):
    return isinstance(g, type(MultiPolygon()))


def is_polygon(g):
    return isinstance(g, type(Polygon()))


def multy_to_poly(g):
    if is_multypolygon(g):
        if len(g) == 1:
            return get_first_poly(g)
        else:
            return g
    else:
        return g
