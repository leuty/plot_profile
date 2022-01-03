"""Purpose: define command line inputs.

Author: Stephanie Westerhuis

Date: 10/11/2021.
"""
# Standard library
import sys

# Third-party
import click

# Local
from .dwh_retrieve import dwh_retrieve
from .get_icon import get_icon
from .plot_icon import create_plot
from .utils import validtime_from_leadtime

# import ipdb


@click.command()
# options without default value (mandatory to specify by user)
@click.option(
    "--date",
    type=click.DateTime(formats=["%y%m%d%H"]),
    help="MANDATORY: Init date of icon simulation: YYMMDDHH.",
)
@click.option(
    "--folder",
    type=str,
    help="MANDATORY: Path to main folder with icon output. Here should be a subfolder named after the date containing nc-files.",
)
@click.option(
    "--var",
    type=click.Choice(
        [
            "temp",
            "qc",
            "qv",
            "clc",
            "ddt_t_rad_lw",
            "ddt_t_rad_sw",
            "qc_dia",
            "qv_dia",
            "qi_dia",
        ],
        case_sensitive=True,
    ),
    multiple=True,
    help="MANDATORY: Variable name(s).",
)
# options with default value
@click.option(
    "--add_clouds",
    is_flag=True,
    help="Show clouds on plot. Def: False",
)
@click.option(
    "--relhum_thresh",
    default=98,
    type=float,
    help="Relative humidity threshold for clouds. Def: 98",
)
@click.option(
    "--add_rs",
    type=int,
    multiple=True,
    help="Add radiosounding for specified leadtime. Def: None",
)
@click.option("--alt_bot", type=int, help="Altitude bottom. Def: surface.")
@click.option("--alt_top", default=2000, type=int, help="Altitude top. Def: 2000")
@click.option(
    "--appendix", type=str, help="String to append to output filename. Def: None"
)
@click.option(
    "--datatypes",
    type=click.Choice(
        [
            "eps",
            "jpeg",
            "jpg",
            "pdf",
            "pgf",
            "png",
            "ps",
            "raw",
            "rgba",
            "svg",
            "svgz",
            "tif",
            "tiff",
        ],
        case_sensitive=True,
    ),
    multiple=True,
    default=[
        "png",
    ],
    help="Choose data type(s) of final result. Def: png",
)
@click.option("--ind", type=int, help="Index of location (known from previous runs).")
@click.option(
    "--grid",
    type=str,
    default="/store/s83/swester/grids/HEIGHT_ICON-1E.nc",
    help="Icon file containing HEIGHT field. Def: ICON-1E operational 2021",
)
@click.option(
    "--leadtime",
    type=int,
    multiple=True,
    default=(0,),
    help="Leadtime(s) to be shown in one plot. Def: 0.",
)
@click.option(
    "--lat", default=46.81281, type=float, help="Latitude of location. Def: 46.81 (PAY)"
)
@click.option(
    "--lon", default=6.94363, type=float, help="Longitude of location. Def: 6.94 (PAY)"
)
@click.option("--loc", default="pay", type=str, help="Name of location. Def: pay")
@click.option("--model", default="icon-1", type=str, help="NWP model name. Def: icon-1")
@click.option(
    "--outpath",
    type=str,
    help="Path to folder where the plots should be saved. Def: /scratch/USER/tmp",
)
@click.option(
    "--show_grid",
    is_flag=True,
    help="Show grid on plot. Flag, def: False",
)
@click.option(
    "--show_marker",
    is_flag=True,
    help="Add markers (o). Flag, def: False",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Output details on what is happening.",
)
@click.option(
    "--xmin",
    type=float,
    multiple=True,
    help="Minimum value of xaxis. Def: Fits values.",
)
@click.option(
    "--xmax",
    type=float,
    multiple=True,
    help="Maximum value of xaxis. Def: Fits values.",
)
@click.option(
    "--xrange_fix",
    is_flag=True,
    help="Use fix xrange from variable dataframe. Overwrites specified xmin and xmax. Flag, def: False",
)
@click.option(
    "--zeroline",
    is_flag=True,
    help="Show grid on plot. Flag, def: False",
)
def main(
    *,
    date: str,
    folder: str,
    var: str,
    add_clouds: bool,
    relhum_thresh: float,
    add_rs: int,
    alt_bot: int,
    alt_top: int,
    appendix: str,
    datatypes: tuple,
    grid: str,
    ind: int,
    leadtime: int,
    lat: float,
    lon: float,
    loc: str,
    model: str,
    outpath: str,
    show_grid: bool,
    show_marker: bool,
    zeroline: bool,
    verbose: bool,
    xmin: tuple,
    xmax: tuple,
    xrange_fix: bool,
):
    """Plot vertical profiles of variables from ICON simulation.

    If 1, 3, or more variables are specified, each will be plotted individually.
    If 2 variables are given, they will be shown in the same figure.

    Example command:
    plot_icon_profiles --date 21111812 --folder /scratch/swester/output_icon/ICON-1/ --var temp --leadtime 11 --leadtime 12

    Model output is expected to be in netcdf-format in a sub-folder named after the given date.

    """
    # A) retrieve data from ICON forecasts
    ######################################
    data_dict = get_icon(
        folder=folder,
        date=date,
        leadtime=leadtime,
        lat=lat,
        lon=lon,
        ind=ind,
        grid=grid,
        variables_list=var,
        alt_bot=alt_bot,
        alt_top=alt_top,
        verbose=verbose,
    )

    # B) retrieve observational data
    ################################
    if add_rs or add_clouds:
        if len(var) == 2:
            print(f"! --add_rs does not work for 2-variable-plot!")
            sys.exit(1)

        else:
            if verbose:
                print("Retrieving radiosounding from DWH.")

            # list of timestamps for which radiosounding is retrieved
            rs_timestamps = [validtime_from_leadtime(date, lt) for lt in add_rs]

            # create obs_dict (like data_dict)
            obs_dict = {"rs": {tt: None for tt in rs_timestamps}}

            # determine variables which should be retrieved
            if var[0] in ["temp", "dewp_temp", "wind_dir", "wind_vel"] and add_clouds:
                rs_var = (var[0], "rel_hum")
            elif var[0] == "rel_hum" or add_clouds:
                rs_var = ("rel_hum",)
            elif var[0] in ["temp", "dewp_temp", "wind_dir", "wind_vel"]:
                rs_var = (var[0],)
            else:
                print(f"--add_rs specified but no matching 1st variable: {var[0]}")
                sys.exit(1)

            # loop over timestamps and fill data_dict
            for timestamp in rs_timestamps:
                obs_dict["rs"][timestamp] = dwh_retrieve(
                    device="rs",
                    station="pay",
                    vars=rs_var,
                    timestamps=timestamp.strftime("%Y%m%d%H%M"),
                    verbose=verbose,
                )

    else:
        obs_dict = None

    # C) create plot
    ################
    create_plot(
        variables_list=var,
        data_dict=data_dict,
        obs_dict=obs_dict,
        outpath=outpath,
        date=date,
        add_clouds=add_clouds,
        relhum_thresh=relhum_thresh,
        alt_bot=alt_bot,
        alt_top=alt_top,
        loc=loc,
        model=model,
        appendix=appendix,
        xmin=xmin,
        xmax=xmax,
        xrange_fix=xrange_fix,
        datatypes=datatypes,
        verbose=verbose,
        show_grid=show_grid,
        show_marker=show_marker,
        zeroline=zeroline,
    )

    print("--- done")