<?php
/**
 * MythTV MythBackend Script for MythBoxee
 *
 * Name: MythBoxee MythTV Backend Script
 * Website: http://erikkristensen.com/project/mythboxee
 * License: MIT License
 * Version: 2.0-RC1
 * 
 * 
 * Author: Erik Kristensen
 * Email: erik@erikkristensen.com
 * Website: http://erikkristensen.com
 * 
 * 
 * This software is released under the MIT License.
 * 
 * Copyright (c) 2010 Erik Kristensen
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

/**
 * Set the relative path to the webroot to how Boxee will access your recordings.
 * For example if you create symlink in the document root called "recordings" to your 
 * recordings directory where all the mpeg2 get stored your path will be 'recordings'.
 * NOTE: there is NO trailing or beginning slash!!!!!!
 */
$config['RecordingsPath'] = '';

/**
 * This script needs to know the hostname or IP of this system
 * so it can link back to the webserver for the media. Leave this
 * value null if you want the script to try and automatically detect
 * the IP.
 */
$config['HostnameIP'] = null;

/*
 * Leave these set to null if you want the script to find the 
 * MySQL credentials for MythTV automatically, if you are getting 
 * an error using the automatic method, add your MySQL credentials
 * here.
 */
$config['DBHostName'] = null;
$config['DBUserName'] = null;
$config['DBName'] = null;
$config['DBPassword'] = null;

//--------------------------------------------//
// DO NOT EDIT ANYTHING BELOW THIS POINT!     //
//--------------------------------------------//

if (!isset($config['RecordingsPath']))
{
	die('Configuration Error: Please set the variable $config[RecordingsPath] in at the top of this file.');
}

if (!file_exists('/home/mythtv/.mythtv/mysql.txt') && !isset($config['database']['username']))
{
	die('Oops! I could not find the mysql credentials for MythTV!');
}

if (file_exists('/home/mythtv/.mythtv/mysql.txt'))
{
	$lines = @file('/home/mythtv/.mythtv/mysql.txt') or die('Error: Something went wrong! Could not access the file where the MySQL credentials are!');
	for ($x=0; $x<count($lines); $x++)
	{
		list($name,$value) = split('=',$lines[$x]);
		$config[$name] = trim($value);
	}
}

/**
 * Automatically get the IP of this server
 */
if ($config['HostnameIP'] == null)
{
	$config['HostnameIP'] = $_SERVER['SERVER_ADDR'];
}

/**
 * Name of the script, this is if people decide to change the name of the script...
 */
$config['script_name'] = $_SERVER['SCRIPT_NAME'];

/**
 * Make our connection to the database.
 */
@mysql_connect($config['DBHostName'], $config['DBUserName'], $config['DBPassword']) or die('Error: Unable to connect to the database! ('.mysql_error().')');
@mysql_select_db($config['DBName']);

/**
 * Detect if a request is being passed to the script.
 * Looking for Type to be set, then Queue or Show and if Show then a Title
 * From that information we build out the RSS that Boxee needs.
 */
if (isset($_REQUEST['type']) && $_REQUEST['type'] == 'show'):

	$channel_title = 'MythTV Recorded Programs';
	$channel_descr = 'My Recorded Programs from MythTV';

	$title = str_replace("_", " ", $_REQUEST['title']);

	$sql = "SELECT * FROM recorded WHERE title = '{$title}' ORDER BY originalairdate DESC";
	$qry = mysql_query($sql);		
?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:boxee="as http://boxee.tv/spec/rss/">
	<channel>
		<title><?php echo $channel_title; ?></title>
		<link>http://www.mythtv.org/</link>
		<description><?php echo $channel_descr; ?></description>
<?php
	while ($obj = mysql_fetch_object($qry)):
		$runtime = strtotime($obj->progend) - strtotime($obj->progstart);
		$content_url = "http://{$config['HostnameIP']}/{$config['RecordingsPath']}/{$obj->basename}";
		$thumbnail_url = $content_url . ".png";
?>
		<item>
			<title><?php echo $obj->subtitle; ?></title>
			<description><?php echo $obj->description; ?></description>
			<media:content url="<?php echo $content_url; ?>" type="video/mpeg" duration="<?php echo $runtime; ?>" />
			<media:thumbnail url="<?php echo $thumbnail_url; ?>" />
			<media:category scheme="urn:boxee:genre"><?php echo $obj->category; ?></media:category>
			<boxee:runtime><?php echo gmdate("H:i:s", $runtime); ?></boxee:runtime>
			<boxee:content_type>tv</boxee:content_type>
			<boxee:tv-show-title><?php echo $obj->subtitle; ?></boxee:tv-show-title>
			<boxee:release-date><?php echo $obj->originalairdate; ?></boxee:release-date>
			<pubDate><?php echo date("D, j M Y G:i:s T", strtotime($obj->originalairdate)); ?></pubDate>
		</item>
<?php
	endwhile; ?>
	</channel>
</rss>
<?php
elseif (isset($_REQUEST['type']) && $_REQUEST['type'] == 'verify'):
	header("HTTP/1.0 200 Ok");
else:
$sql = "SELECT * FROM recorded GROUP BY title";
$qry = mysql_query($sql);
?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:boxee="as http://boxee.tv/spec/rss/">
	<channel>
		<title>MythTV Recorded Programs</title>
		<link>http://www.mythtv.org/</link>
		<description>My Recorded Programs from MythTV</description>
<?php
		while ($obj = mysql_fetch_object($qry)): ?>
		<item>
			<title><?php echo $obj->title; ?></title>
			<link>rss://<?php echo $config['HostnameIP']; ?><?php echo $config['script_name']; ?>?type=show&amp;title=<?php echo strtoupper(str_replace(" ", "_", $obj->title)); ?></link>
			<media:thumbnail url="http://<?php echo $config['HostnameIP']; ?>/<?php echo $config['RecordingsPath']; ?>/<?php echo $obj->basename; ?>.png" />
		</item>
<?php
		endwhile; ?>
	</channel>
</rss>
<?php endif; ?>
